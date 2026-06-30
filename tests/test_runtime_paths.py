from pathlib import Path

from glist_pipeline.runtime_paths import get_config_dir, get_workspace_root


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "German_Listening"
    (repo / "configs").mkdir(parents=True)
    (repo / "Outputs").mkdir()
    (repo / "Transcripts").mkdir()
    (repo / "Audios").mkdir()
    return repo


def test_frozen_workspace_root_prefers_exe_parent_repo(monkeypatch, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    exe = repo / "dist" / "GermanListeningCLI.exe"
    exe.parent.mkdir()
    exe.write_text("stub", encoding="utf-8")

    monkeypatch.setattr("glist_pipeline.runtime_paths.sys.frozen", True, raising=False)
    monkeypatch.setattr("glist_pipeline.runtime_paths.sys.executable", str(exe), raising=False)
    monkeypatch.delenv("_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)

    assert get_workspace_root() == repo.resolve()
    assert get_config_dir() == (repo / "configs").resolve()


def test_frozen_config_dir_falls_back_to_meipass(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "no-repo-shape"
    repo.mkdir()
    exe = repo / "GermanListeningCLI.exe"
    exe.write_text("stub", encoding="utf-8")
    meipass = tmp_path / "_MEI12345"
    (meipass / "configs").mkdir(parents=True)

    monkeypatch.setattr("glist_pipeline.runtime_paths.sys.frozen", True, raising=False)
    monkeypatch.setattr("glist_pipeline.runtime_paths.sys.executable", str(exe), raising=False)
    monkeypatch.setattr("glist_pipeline.runtime_paths.sys._MEIPASS", str(meipass), raising=False)
    monkeypatch.chdir(tmp_path)

    assert get_config_dir() == (meipass / "configs").resolve()
