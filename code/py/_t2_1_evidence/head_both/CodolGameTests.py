#!/usr/bin/env python3

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import CodolGame


class CodolGameTests(unittest.TestCase):
    def test_role_state_roundtrip_and_stale_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            CodolGame.write_process_state(
                game_directory,
                [
                    {"role": "dedicated", "pid": 101},
                    {"role": "client", "pid": 202},
                ],
                30001,
                30002,
                {"pid": 99, "executable": CodolGame.ROOM_OWNER_NAME},
                30003,
            )
            state = CodolGame.read_process_state(game_directory)
            self.assertIsNotNone(state)
            self.assertEqual(state["dedicatedControlPort"], 30001)
            self.assertEqual(state["roomOwnerPort"], 30003)
            self.assertEqual(
                state["roomOwner"],
                {"pid": 99, "executable": CodolGame.ROOM_OWNER_NAME},
            )
            self.assertFalse(
                CodolGame.process_state_path(game_directory)
                .with_suffix(".json.writing")
                .exists()
            )
            with mock.patch.object(CodolGame, "running_pids", return_value=[101, 202]):
                self.assertEqual(CodolGame.role_pids(game_directory, "dedicated"), [101])
                self.assertEqual(CodolGame.role_pids(game_directory, "client"), [202])
            with mock.patch.object(CodolGame, "running_pids", return_value=[202]):
                self.assertEqual(CodolGame.role_pids(game_directory, "dedicated"), [])

    def test_tracked_dedicated_is_not_guessed_as_client(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            CodolGame.write_process_state(
                game_directory,
                [
                    {"role": "dedicated", "pid": 101},
                    {"role": "client", "pid": 202},
                ],
                30001,
                30002,
            )
            with mock.patch.object(CodolGame, "running_pids", return_value=[101]):
                self.assertEqual(CodolGame.role_pids(game_directory, "dedicated"), [101])
                self.assertEqual(CodolGame.role_pids(game_directory, "client"), [])

    def test_combined_state_is_a_client_compatibility_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            CodolGame.write_process_state(
                game_directory,
                [{"role": "combined", "pid": 303}],
                28961,
                28962,
            )
            with mock.patch.object(CodolGame, "running_pids", return_value=[303]):
                self.assertEqual(CodolGame.role_pids(game_directory, "client"), [303])
                self.assertEqual(CodolGame.role_pids(game_directory, "dedicated"), [])

    def test_process_environment_is_explicit_and_isolated(self) -> None:
        with mock.patch.dict(os.environ, {"OLMOD_PROCESS_ROLE": "old"}, clear=False):
            environment = CodolGame.process_environment("dedicated", 31001, 31002)
            self.assertEqual(environment["OLMOD_PROCESS_ROLE"], "dedicated")
            self.assertEqual(environment["OLMOD_DEDICATED_CONTROL_PORT"], "31001")
            self.assertEqual(environment["OLMOD_CLIENT_BRIDGE_PORT"], "31002")
            self.assertEqual(environment["OLMOD_CONSOLE_LOG"], "1")
            self.assertEqual(environment["OLMOD_CLIENT_INSTANCE"], "1")
            self.assertEqual(os.environ["OLMOD_PROCESS_ROLE"], "old")

    def test_secondary_client_environment_has_independent_runtime_identity(self) -> None:
        environment = CodolGame.process_environment(
            "client",
            31001,
            31003,
            client_instance=2,
            platform_user_id="01100001DEADC0DF",
        )
        self.assertEqual(environment["OLMOD_CLIENT_INSTANCE"], "2")
        self.assertEqual(environment["OLMOD_CLIENT_BRIDGE_PORT"], "31003")
        self.assertEqual(environment["OLMOD_PLATFORM_USER_ID"], "01100001DEADC0DF")

    def test_only_dedicated_uses_native_qa_launch_bypass(self) -> None:
        self.assertEqual(CodolGame.launch_arguments("auto", "client"), [])
        self.assertEqual(CodolGame.launch_arguments("auto", "combined"), [])
        self.assertEqual(CodolGame.launch_arguments("auto", "dedicated"), ["-qa"])
        self.assertEqual(
            CodolGame.launch_arguments("offline", "dedicated"),
            [*CodolGame.TARGET_ARGUMENTS, "-qa"],
        )

    def test_invalid_state_is_not_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            path = CodolGame.process_state_path(game_directory)
            path.parent.mkdir(parents=True)
            path.write_text('{"schemaVersion":99,"processes":[]}', encoding="utf-8")
            self.assertIsNone(CodolGame.read_process_state(game_directory))

    def test_dedicated_pair_starts_client_before_patched_dedicated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            target = game_directory / CodolGame.TARGET_NAME
            injector = game_directory / "Ayria" / "Injector32.exe"
            with (
                mock.patch.object(CodolGame, "running_pids", return_value=[]),
                mock.patch.object(CodolGame, "ports_available", return_value=True),
                mock.patch.object(
                    CodolGame, "validate_launch_files", return_value=(target, injector)
                ),
                mock.patch.object(
                    CodolGame, "launch_process", side_effect=[111, 222]
                ) as launch_process,
                mock.patch.object(CodolGame, "launch_room_owner", return_value=99),
                mock.patch.object(CodolGame, "write_process_state") as write_state,
                mock.patch.object(CodolGame, "print_status"),
            ):
                result = CodolGame.launch_dedicated_pair(
                    game_directory, 20.0, "auto", 30001, 30002
                )
            self.assertEqual(result, 0)
            self.assertEqual(
                [call.args[5] for call in launch_process.call_args_list],
                ["client", "dedicated"],
            )
            self.assertEqual(
                [call.args[8] for call in launch_process.call_args_list],
                [30002, 30001],
            )
            self.assertEqual(
                write_state.call_args.args[1],
                [
                    {"role": "dedicated", "pid": 222},
                    {
                        "role": "client",
                        "pid": 111,
                        "instance": 1,
                        "bridgePort": 30002,
                    },
                ],
            )
            self.assertEqual(
                write_state.call_args.kwargs,
                {},
            )
            self.assertEqual(
                write_state.call_args.args[4],
                {"pid": 99, "executable": CodolGame.ROOM_OWNER_NAME},
            )
            self.assertEqual(write_state.call_args.args[5], 28970)

    def test_dedicated_pair_stops_when_room_owner_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            target = game_directory / CodolGame.TARGET_NAME
            injector = game_directory / "Ayria" / "Injector32.exe"
            with (
                mock.patch.object(CodolGame, "running_pids", return_value=[]),
                mock.patch.object(CodolGame, "ports_available", return_value=True),
                mock.patch.object(
                    CodolGame, "validate_launch_files", return_value=(target, injector)
                ),
                mock.patch.object(CodolGame, "launch_room_owner", return_value=None),
                mock.patch.object(CodolGame, "launch_process") as launch_process,
            ):
                result = CodolGame.launch_dedicated_pair(
                    game_directory, 20.0, "auto", 30001, 30002, 30003
                )
            self.assertEqual(result, 3)
            launch_process.assert_not_called()

    def test_dedicated_pair_cleans_room_owner_when_client_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            target = game_directory / CodolGame.TARGET_NAME
            injector = game_directory / "Ayria" / "Injector32.exe"
            with (
                mock.patch.object(CodolGame, "running_pids", return_value=[]),
                mock.patch.object(CodolGame, "ports_available", return_value=True),
                mock.patch.object(
                    CodolGame, "validate_launch_files", return_value=(target, injector)
                ),
                mock.patch.object(CodolGame, "launch_room_owner", return_value=99),
                mock.patch.object(CodolGame, "launch_process", return_value=None),
                mock.patch.object(CodolGame, "terminate_pids") as terminate,
            ):
                result = CodolGame.launch_dedicated_pair(
                    game_directory, 20.0, "auto", 30001, 30002, 30003
                )
            self.assertEqual(result, 3)
            terminate.assert_called_once_with([99])

    def test_dedicated_pair_rolls_back_client_when_dedicated_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            target = game_directory / CodolGame.TARGET_NAME
            injector = game_directory / "Ayria" / "Injector32.exe"
            with (
                mock.patch.object(CodolGame, "running_pids", return_value=[]),
                mock.patch.object(CodolGame, "ports_available", return_value=True),
                mock.patch.object(
                    CodolGame, "validate_launch_files", return_value=(target, injector)
                ),
                mock.patch.object(CodolGame, "launch_process", side_effect=[111, None]),
                mock.patch.object(CodolGame, "launch_room_owner", return_value=99),
                mock.patch.object(CodolGame, "write_process_state"),
                mock.patch.object(CodolGame, "terminate_pids") as terminate,
            ):
                result = CodolGame.launch_dedicated_pair(
                    game_directory, 20.0, "auto", 30001, 30002
                )
            self.assertEqual(result, 3)
            self.assertEqual(
                terminate.call_args_list,
                [mock.call([111, 99])],
            )

    def test_client_recovery_reuses_tracked_dedicated_and_ports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            target = game_directory / CodolGame.TARGET_NAME
            injector = game_directory / "Ayria" / "Injector32.exe"
            state = {
                "schemaVersion": CodolGame.PROCESS_STATE_SCHEMA,
                "gameExecutable": CodolGame.TARGET_NAME,
                "dedicatedControlPort": 30001,
                "clientBridgePort": 30002,
                "roomOwnerPort": 30003,
                "roomOwner": {
                    "pid": 99,
                    "executable": CodolGame.ROOM_OWNER_NAME,
                },
                "processes": [
                    {"role": "dedicated", "pid": 222},
                    {"role": "client", "pid": 111},
                ],
            }
            with (
                mock.patch.object(CodolGame, "read_process_state", return_value=state),
                mock.patch.object(CodolGame, "running_pids", return_value=[222]),
                mock.patch.object(
                    CodolGame, "ports_available", side_effect=[False, True, False]
                ),
                mock.patch.object(
                    CodolGame,
                    "process_image_name",
                    return_value=CodolGame.ROOM_OWNER_NAME,
                ),
                mock.patch.object(
                    CodolGame, "validate_launch_files", return_value=(target, injector)
                ),
                mock.patch.object(CodolGame, "launch_process", return_value=333) as launch,
                mock.patch.object(CodolGame, "write_process_state") as write_state,
                mock.patch.object(CodolGame, "print_status"),
            ):
                result = CodolGame.launch_client_for_dedicated(
                    game_directory, 20.0, "auto"
                )
            self.assertEqual(result, 0)
            self.assertEqual(launch.call_args.args[5], "client")
            self.assertEqual(launch.call_args.args[8], 30002)
            self.assertEqual(launch.call_args.args[9], 30003)
            self.assertEqual(
                write_state.call_args.args[1],
                [
                    {"role": "dedicated", "pid": 222},
                    {
                        "role": "client",
                        "pid": 333,
                        "instance": 1,
                        "bridgePort": 30002,
                    },
                ],
            )
            self.assertEqual(
                write_state.call_args.args[4],
                {"pid": 99, "executable": CodolGame.ROOM_OWNER_NAME},
            )

    def test_client_recovery_rejects_missing_room_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            state = {
                "schemaVersion": CodolGame.PROCESS_STATE_SCHEMA,
                "gameExecutable": CodolGame.TARGET_NAME,
                "dedicatedControlPort": 30001,
                "clientBridgePort": 30002,
                "roomOwnerPort": 30003,
                "roomOwner": {
                    "pid": 99,
                    "executable": CodolGame.ROOM_OWNER_NAME,
                },
                "processes": [{"role": "dedicated", "pid": 222}],
            }
            with (
                mock.patch.object(CodolGame, "read_process_state", return_value=state),
                mock.patch.object(CodolGame, "running_pids", return_value=[222]),
                mock.patch.object(CodolGame, "ports_available", side_effect=[False, True]),
                mock.patch.object(CodolGame, "process_image_name", return_value=None),
                mock.patch.object(CodolGame, "launch_process") as launch,
            ):
                result = CodolGame.launch_client_for_dedicated(
                    game_directory, 20.0, "auto"
                )
            self.assertEqual(result, 2)
            launch.assert_not_called()

    def test_secondary_client_attaches_with_unique_identity_and_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            account = CodolGame.player_account_path(
                game_directory, "01100001DEADC0DF"
            )
            account.mkdir(parents=True)
            (account / "Identity.json").write_text("{}", encoding="ascii")
            target = game_directory / CodolGame.TARGET_NAME
            injector = game_directory / "Ayria" / "Injector32.exe"
            state = {
                "schemaVersion": CodolGame.PROCESS_STATE_SCHEMA,
                "gameExecutable": CodolGame.TARGET_NAME,
                "dedicatedControlPort": 30001,
                "clientBridgePort": 30002,
                "roomOwnerPort": 30003,
                "roomOwner": {
                    "pid": 99,
                    "executable": CodolGame.ROOM_OWNER_NAME,
                },
                "processes": [
                    {"role": "dedicated", "pid": 222},
                    {
                        "role": "client",
                        "pid": 111,
                        "instance": 1,
                        "userId": "01100001DEADC0DE",
                        "bridgePort": 30002,
                    },
                ],
            }
            with (
                mock.patch.object(CodolGame, "read_process_state", return_value=state),
                mock.patch.object(CodolGame, "running_pids", return_value=[111, 222]),
                mock.patch.object(
                    CodolGame, "ports_available", side_effect=[False, True, False]
                ),
                mock.patch.object(
                    CodolGame, "process_image_name", return_value=CodolGame.ROOM_OWNER_NAME
                ),
                mock.patch.object(
                    CodolGame, "validate_launch_files", return_value=(target, injector)
                ),
                mock.patch.object(CodolGame, "launch_process", return_value=333) as launch,
                mock.patch.object(CodolGame, "write_process_state") as write_state,
                mock.patch.object(CodolGame, "print_status"),
            ):
                result = CodolGame.launch_client_for_dedicated(
                    game_directory,
                    20.0,
                    "auto",
                    client_instance=2,
                    platform_user_id="DEADC0DF",
                    requested_bridge_port=30004,
                )
            self.assertEqual(result, 0)
            self.assertEqual(launch.call_args.args[8:12], (30004, 30003, 2, "01100001DEADC0DF"))
            self.assertEqual(write_state.call_args.args[3], 30002)
            self.assertEqual(
                write_state.call_args.args[1][-1],
                {
                    "role": "client",
                    "pid": 333,
                    "instance": 2,
                    "bridgePort": 30004,
                    "userId": "01100001DEADC0DF",
                },
            )

    def test_secondary_client_rejects_duplicate_instance_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            state = {
                "schemaVersion": CodolGame.PROCESS_STATE_SCHEMA,
                "gameExecutable": CodolGame.TARGET_NAME,
                "dedicatedControlPort": 30001,
                "clientBridgePort": 30002,
                "roomOwnerPort": 30003,
                "roomOwner": {"pid": 99, "executable": CodolGame.ROOM_OWNER_NAME},
                "processes": [
                    {"role": "dedicated", "pid": 222},
                    {
                        "role": "client",
                        "pid": 111,
                        "instance": 2,
                        "userId": "01100001DEADC0DE",
                        "bridgePort": 30002,
                    },
                ],
            }
            with (
                mock.patch.object(CodolGame, "read_process_state", return_value=state),
                mock.patch.object(CodolGame, "running_pids", return_value=[111, 222]),
                mock.patch.object(CodolGame, "ports_available", side_effect=[False, True, False]),
                mock.patch.object(
                    CodolGame, "process_image_name", return_value=CodolGame.ROOM_OWNER_NAME
                ),
                mock.patch.object(CodolGame, "launch_process") as launch,
            ):
                result = CodolGame.launch_client_for_dedicated(
                    game_directory, 20.0, "auto", 2, "DEADC0DF", 30004
                )
            self.assertEqual(result, 2)
            launch.assert_not_called()

    def test_stop_only_terminates_matching_room_owner_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            state = {
                "schemaVersion": CodolGame.PROCESS_STATE_SCHEMA,
                "gameExecutable": CodolGame.TARGET_NAME,
                "processes": [],
                "roomOwner": {
                    "pid": 99,
                    "executable": CodolGame.ROOM_OWNER_NAME,
                },
            }
            with (
                mock.patch.object(CodolGame, "read_process_state", return_value=state),
                mock.patch.object(CodolGame, "running_pids", return_value=[]),
                mock.patch.object(CodolGame, "process_image_name", return_value="other.exe"),
                mock.patch.object(CodolGame, "terminate_pids") as terminate,
            ):
                self.assertEqual(CodolGame.stop(game_directory), 0)
            terminate.assert_not_called()

    def test_client_recovery_rejects_untracked_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game_directory = Path(temporary)
            state = {
                "schemaVersion": CodolGame.PROCESS_STATE_SCHEMA,
                "gameExecutable": CodolGame.TARGET_NAME,
                "dedicatedControlPort": 30001,
                "clientBridgePort": 30002,
                "processes": [{"role": "dedicated", "pid": 222}],
            }
            with (
                mock.patch.object(CodolGame, "read_process_state", return_value=state),
                mock.patch.object(CodolGame, "running_pids", return_value=[222, 444]),
                mock.patch.object(CodolGame, "print_status"),
                mock.patch.object(CodolGame, "launch_process") as launch,
            ):
                result = CodolGame.launch_client_for_dedicated(
                    game_directory, 20.0, "auto"
                )
            self.assertEqual(result, 2)
            launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
