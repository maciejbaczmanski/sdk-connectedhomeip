# Copyright (c) 2024 Nordic Semiconductor ASA
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause

import argparse
import tempfile
import shutil
import re
import os
import sys

from textwrap import dedent
from pathlib import Path

from west import log
from west.commands import CommandError, WestCommand

from zap_common import existing_file_path, existing_dir_path, find_zap, ZapInstaller, DEFAULT_MATTER_PATH


class ZapGenerate(WestCommand):

    def __init__(self):
        super().__init__(
            'zap-generate',  # gets stored as self.name
            'Generate Matter data model files with ZAP',  # self.help
            # self.description:
            dedent('''
            Generate Matter data model files with the use of ZAP Tool
            based on the .zap template file defined for your application.'''))

    def do_add_parser(self, parser_adder):
        parser = parser_adder.add_parser(self.name,
                                         help=self.help,
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=self.description)
        parser.add_argument('-z', '--zap-file', type=existing_file_path,
                            help='Path to data model configuration file (*.zap)')
        parser.add_argument('-o', '--output', type=existing_dir_path,
                            help='Path where to store the generated files')
        parser.add_argument('-m', '--matter-path', type=existing_dir_path,
                            default=DEFAULT_MATTER_PATH, help='Path to Matter SDK')
        parser.add_argument('-f', '--full', action='store_true', help='Generate full data model files')
        return parser

    def do_run(self, args, unknown_args):
        if args.zap_file:
            zap_file_path = args.zap_file.absolute()
        else:
            zap_file_path = find_zap()

        if not zap_file_path:
            raise CommandError("No valid .zap file provided")

        if args.output:
            output_path = args.output.absolute()
        else:
            output_path = zap_file_path.parent / "zap-generated"

        app_templates_path = args.matter_path / "src/app/zap-templates/app-templates.json"
        zap_generate_path = args.matter_path / "scripts/tools/zap/generate.py"

        zap_installer = ZapInstaller(args.matter_path)
        zap_installer.update_zap_if_needed()

        # make sure that the generate.py script uses the proper zap_cli binary (handled by west)
        os.environ["ZAP_INSTALL_PATH"] = str(zap_installer.get_zap_cli_path().parent.absolute())

        cmd = [sys.executable, zap_generate_path]
        cmd += [zap_file_path]


        self.check_call([str(x) for x in cmd + ["-o", output_path] + ["-t", app_templates_path]])
        if args.full:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                shutil.copytree(args.matter_path / "src/app/common/templates", tmpdir / "templates", dirs_exist_ok=True)
                shutil.copytree(args.matter_path / "src/app/zap-templates", tmpdir / "zap-templates", dirs_exist_ok=True)
                templates_json_path = tmpdir / "templates/templates.json"
                with open(templates_json_path, 'r+') as file:
                    content = file.read()
                    content = content.replace("../../zap-templates", "../zap-templates")
                    file.seek(0)
                    file.write(content)
                    file.truncate()

                # for zapt_file in (tmpdir / "zap-templates").rglob("*.zapt"):
                #     with open(zapt_file, 'r+') as file:
                #         content = file.read()
                #         content = re.sub(r'#include <app-common/zap-generated/(.*?)>', r'#include "zap-generated/\1"', content, flags=re.MULTILINE)
                #         file.seek(0)
                #         file.write(content)
                #         file.truncate()
                self.check_call([str(x) for x in cmd + ["-o", output_path / "app-common/zap-generated"] + ["-t", tmpdir / "templates/templates.json"]])
        # else:

        log.inf(f"Done. Files generated in {output_path}")
