#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manifest_cloner.py - Binary AndroidManifest.xml (AXML) Package & Authority Cloner

Directly parses and updates binary compiled AXML files:
1. Re-scopes package identifier to `<pkg>.<suffix>` (e.g. com.oplus.keyboard.en).
2. Automatically updates ContentProvider authorities, custom permissions, and actions.
3. Prevents OEM installation conflicts (INSTALL_FAILED_UPDATE_INCOMPATIBLE & INSTALL_FAILED_CONFLICTING_PROVIDER).
4. Maintains 100% binary AXML chunk integrity without requiring aapt2 recompilation.
"""

import struct
import re

class ManifestCloner:
    def __init__(self, clone_suffix: str = ".en"):
        self.clone_suffix = clone_suffix

    def clone_manifest_data(self, data: bytes) -> (bytes, str, str):
        """
        Parses binary AXML, clones the package name & authorities, and returns rebuilt data.
        Returns: (rebuilt_data, old_package_name, new_package_name)
        """
        magic, total_size = struct.unpack('<II', data[0:8])
        if magic != 0x00080003:
            raise ValueError(f"Invalid AXML magic: {hex(magic)} (expected 0x00080003)")

        # String pool is at offset 8
        sp_type, sp_header_size, sp_size = struct.unpack('<HHI', data[8:16])
        if sp_type != 0x0001:
            raise ValueError(f"Invalid AXML StringPool type: {hex(sp_type)}")

        scnt, sstyle, sflags, sstr_start, sstyle_start = struct.unpack('<IIIII', data[16:36])
        is_utf8 = bool(sflags & (1 << 8))

        offsets = list(struct.unpack(f'<{scnt}I', data[36:36+scnt*4]))
        str_block = data[8+sstr_start : 8+sp_size]

        strings = []
        for off in offsets:
            p = off
            if is_utf8:
                b1 = str_block[p]
                p += 2 if (b1 & 0x80) else 1
                b2 = str_block[p]
                if b2 & 0x80:
                    u8_len = ((b2 & 0x7f) << 8) | str_block[p+1]
                    p += 2
                else:
                    u8_len = b2
                    p += 1
                s = str_block[p:p+u8_len].decode('utf-8', errors='ignore')
            else:
                u16_len = struct.unpack('<H', str_block[p:p+2])[0]
                s = str_block[p+2:p+2+u16_len*2].decode('utf-16le', errors='ignore')
            strings.append(s)

        # Identify base package name (most frequent common domain prefix)
        pkg_candidates = [s for s in strings if re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$', s)]
        # Filter out android namespaces or standard libraries
        pkg_candidates = [s for s in pkg_candidates if not (s.startswith('android.') or s.startswith('androidx.') or s.startswith('kotlin.'))]

        if not pkg_candidates:
            raise ValueError("Could not automatically identify base package in manifest strings")

        # Pick the shortest root package among candidates
        base_pkg = min(pkg_candidates, key=lambda s: len(s.split('.')))
        new_pkg = base_pkg + self.clone_suffix if not base_pkg.endswith(self.clone_suffix) else base_pkg

        print(f"[Manifest] Identified base package: {base_pkg} -> Cloned to: {new_pkg}")

        # Clone strings
        modified_count = 0
        new_strings = []
        for s in strings:
            if s == base_pkg:
                new_strings.append(new_pkg)
                modified_count += 1
            elif s.startswith(base_pkg + '.') and not s.startswith(new_pkg):
                # Check if it is a provider authority or permission
                # E.g. com.oplus.keyboard.provider.file -> com.oplus.keyboard.en.provider.file
                cloned_s = s.replace(base_pkg, new_pkg, 1)
                new_strings.append(cloned_s)
                modified_count += 1
            else:
                new_strings.append(s)

        print(f"[Manifest] Cloned {modified_count} package, authority, and permission references.")

        # Re-encode AXML string pool
        new_str_block = bytearray()
        new_offsets = []

        if is_utf8:
            for s in new_strings:
                new_offsets.append(len(new_str_block))
                u16_len = len(s)
                u8_bytes = s.encode('utf-8')
                u8_len = len(u8_bytes)
                if u16_len > 0x7f:
                    new_str_block.extend([0x80 | ((u16_len >> 8) & 0x7f), u16_len & 0xff])
                else:
                    new_str_block.append(u16_len)
                if u8_len > 0x7f:
                    new_str_block.extend([0x80 | ((u8_len >> 8) & 0x7f), u8_len & 0xff])
                else:
                    new_str_block.append(u8_len)
                new_str_block.extend(u8_bytes)
                new_str_block.append(0)
        else:
            for s in new_strings:
                new_offsets.append(len(new_str_block))
                u16_len = len(s)
                u16_bytes = s.encode('utf-16le')
                new_str_block.extend(struct.pack('<H', u16_len))
                new_str_block.extend(u16_bytes)
                new_str_block.extend(b'\x00\x00')

        # 4-byte padding
        while len(new_str_block) % 4 != 0:
            new_str_block.append(0)

        # Style data if any
        style_block = b''
        if sstyle > 0 and sstyle_start > 0:
            style_block = data[8+sstyle_start : 8+sp_size]

        new_sp_size = sstr_start + len(new_str_block) + len(style_block)
        delta_size = new_sp_size - sp_size
        new_total_size = total_size + delta_size

        new_header = struct.pack('<II', magic, new_total_size)
        new_sp_header = struct.pack('<HHI', sp_type, sp_header_size, new_sp_size) + \
                        struct.pack('<IIIII', scnt, sstyle, sflags, sstr_start, sstyle_start)
        new_offsets_bytes = struct.pack(f'<{scnt}I', *new_offsets)

        rest_of_axml = data[8+sp_size:]

        rebuilt_data = new_header + new_sp_header + new_offsets_bytes + bytes(new_str_block) + style_block + rest_of_axml
        return rebuilt_data, base_pkg, new_pkg

    def clone_manifest_file(self, in_path: str, out_path: str) -> (str, str):
        with open(in_path, 'rb') as f:
            data = f.read()
        rebuilt, base_pkg, new_pkg = self.clone_manifest_data(data)
        with open(out_path, 'wb') as f:
            f.write(rebuilt)
        print(f"[Manifest] Saved cloned manifest to {out_path} ({len(rebuilt)} bytes)")
        return base_pkg, new_pkg
