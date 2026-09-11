from scripts.check_architecture import main


def test_architecture_boundaries() -> None:
    assert main() == 0
