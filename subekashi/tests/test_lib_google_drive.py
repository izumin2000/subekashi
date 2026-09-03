"""
lib/google_drive.py のテスト（Google Drive APIはモック化、#1050）

upload_backup: アップロード先フォルダ・ファイル名の指定、アップロード後にファイルハンドルが解放されることを検証する。
delete_old_backups: 保持件数の境界値（未満・ちょうど・超過）での削除対象の切り出しロジックを検証する。
"""
import os
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from subekashi.lib.google_drive import delete_old_backups, upload_backup


class UploadBackupTest(SimpleTestCase):
    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_uploads_file_with_expected_name(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "backup.sqlite3")
            with open(file_path, "wb") as f:
                f.write(b"dummy")

            upload_backup(file_path, "2026-01-01-00.sqlite3")

            # ファイルハンドルが解放されていなければ削除に失敗する
            os.remove(file_path)

        create_call = mock_service.files.return_value.create
        create_call.assert_called_once()
        self.assertEqual(create_call.call_args.kwargs["body"]["name"], "2026-01-01-00.sqlite3")
        self.assertIn("parents", create_call.call_args.kwargs["body"])
        create_call.return_value.execute.assert_called_once()

    @patch("subekashi.lib.google_drive.MediaIoBaseUpload")
    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_defaults_to_sqlite_mimetype(self, mock_get_service, mock_media_upload):
        mock_get_service.return_value = MagicMock()

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "backup.sqlite3")
            with open(file_path, "wb") as f:
                f.write(b"dummy")

            upload_backup(file_path, "2026-01-01-00.sqlite3")

        self.assertEqual(mock_media_upload.call_args.kwargs["mimetype"], "application/x-sqlite3")

    @patch("subekashi.lib.google_drive.MediaIoBaseUpload")
    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_uses_specified_mimetype(self, mock_get_service, mock_media_upload):
        # #1086: MySQL移行時のmysqldumpダンプ(.sql)アップロード用
        mock_get_service.return_value = MagicMock()

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "backup.sql")
            with open(file_path, "wb") as f:
                f.write(b"dummy")

            upload_backup(file_path, "2026-01-01-00.sql", mimetype="application/sql")

        self.assertEqual(mock_media_upload.call_args.kwargs["mimetype"], "application/sql")


class DeleteOldBackupsTest(SimpleTestCase):
    def _mock_service_with_files(self, names):
        mock_service = MagicMock()
        mock_service.files.return_value.list.return_value.execute.return_value = {
            "files": [{"id": f"id-{name}", "name": name} for name in names]
        }
        return mock_service

    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_no_deletion_when_under_limit(self, mock_get_service):
        mock_service = self._mock_service_with_files(["2026-01-01-00.sqlite3", "2026-01-01-06.sqlite3"])
        mock_get_service.return_value = mock_service

        delete_old_backups(50)

        mock_service.files.return_value.delete.assert_not_called()

    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_no_deletion_when_exactly_at_limit(self, mock_get_service):
        names = [f"file-{i}" for i in range(50)]
        mock_service = self._mock_service_with_files(names)
        mock_get_service.return_value = mock_service

        delete_old_backups(50)

        mock_service.files.return_value.delete.assert_not_called()

    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_no_deletion_when_under_limit_but_more_than_half(self, mock_get_service):
        # 回帰防止テスト: len(files) - keep_nums が負でも0未満（例: 26-50=-24）の場合、
        # files[:負の数] は「末尾から」ではなく実質的に「先頭から」の指定になり得るため
        # （-24は-len(files)=-26より大きい＝スライスが空にならない）、
        # 誤って最も古いファイルを削除してしまうバグが実際に本番で発生した（#1086）
        names = [f"file-{i}" for i in range(26)]
        mock_service = self._mock_service_with_files(names)
        mock_get_service.return_value = mock_service

        delete_old_backups(50)

        mock_service.files.return_value.delete.assert_not_called()

    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_deletes_only_oldest_file_when_over_limit_by_one(self, mock_get_service):
        names = [f"file-{i}" for i in range(51)]
        mock_service = self._mock_service_with_files(names)
        mock_get_service.return_value = mock_service

        delete_old_backups(50)

        mock_service.files.return_value.delete.assert_called_once_with(fileId="id-file-0")

    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_deletes_all_oldest_files_over_limit(self, mock_get_service):
        names = [f"file-{i}" for i in range(54)]
        mock_service = self._mock_service_with_files(names)
        mock_get_service.return_value = mock_service

        delete_old_backups(50)

        delete_call = mock_service.files.return_value.delete
        self.assertEqual(delete_call.call_count, 4)
        deleted_ids = {call.kwargs["fileId"] for call in delete_call.call_args_list}
        self.assertEqual(deleted_ids, {f"id-file-{i}" for i in range(4)})

    @patch("subekashi.lib.google_drive.get_drive_service")
    def test_combines_results_across_multiple_pages(self, mock_get_service):
        # デフォルトpageSize(100件)を超えるファイル数でも、全ページを合算して保持件数を判定すること
        page1 = {
            "nextPageToken": "token-2",
            "files": [{"id": f"id-file-{i}", "name": f"file-{i:03d}"} for i in range(100)],
        }
        page2 = {
            "files": [{"id": f"id-file-{i}", "name": f"file-{i:03d}"} for i in range(100, 105)],
        }
        mock_service = MagicMock()
        mock_service.files.return_value.list.return_value.execute.side_effect = [page1, page2]
        mock_get_service.return_value = mock_service

        delete_old_backups(50)

        delete_call = mock_service.files.return_value.delete
        self.assertEqual(delete_call.call_count, 55)
        deleted_ids = {call.kwargs["fileId"] for call in delete_call.call_args_list}
        self.assertEqual(deleted_ids, {f"id-file-{i}" for i in range(55)})
