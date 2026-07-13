from pathlib import Path

from glist_pipeline import runtime_paths


def test_get_workspace_root_prefers_repo_root_for_frozen_onedir(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    exe_dir = repo_root / "dist" / "GermanListeningCLI"
    exe_dir.mkdir(parents=True)
    (repo_root / "configs").mkdir()
    (repo_root / "Tools" / "src").mkdir(parents=True)
    monkeypatch.setattr(runtime_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_paths.sys, "executable", str(exe_dir / "GermanListeningCLI.exe"), raising=False)
    monkeypatch.setattr(runtime_paths, "_workspace_candidates", lambda: [exe_dir, exe_dir.parent, repo_root])

    assert runtime_paths.get_workspace_root() == repo_root.resolve()


def test_get_config_dir_finds_repo_config_for_frozen_onedir(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    exe_dir = repo_root / "dist" / "GermanListeningCLI"
    exe_dir.mkdir(parents=True)
    config_dir = repo_root / "configs"
    config_dir.mkdir()
    monkeypatch.setattr(runtime_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_paths.sys, "executable", str(exe_dir / "GermanListeningCLI.exe"), raising=False)
    monkeypatch.setattr(runtime_paths, "get_workspace_root", lambda: repo_root.resolve())

    assert runtime_paths.get_config_dir() == config_dir.resolve()
