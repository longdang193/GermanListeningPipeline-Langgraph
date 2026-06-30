from glist_pipeline import cli


def test_run_menu_stays_open_after_action(monkeypatch, capsys) -> None:
    answers = iter(["1", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    calls = {"count": 0}

    def fake_action() -> int:
        calls["count"] += 1
        return 0

    monkeypatch.setattr(cli, "run_menu_action_1", fake_action)

    assert cli.run_menu() == 0
    assert calls["count"] == 1
    out = capsys.readouterr().out
    assert "Action complete. Choose next action or exit." in out
    assert out.count("German_Listening MVP") == 2
