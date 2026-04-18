from tools.rag.slash_commands import SlashCommandRouter


def test_slash_command_router():
    router = SlashCommandRouter()

    assert router.is_slash_command("/help") is True
    assert router.is_slash_command(" /help ") is True
    assert router.is_slash_command("hello") is False

    cmd = router.parse("/help args1 args2")
    assert cmd.name == "help"
    assert cmd.args == ["args1", "args2"]

    # Test empty command
    cmd = router.parse("/")
    assert cmd.name == ""
    res = router.dispatch(cmd)
    assert res.type == "error"

    # Test unknown command
    cmd = router.parse("/unknown_cmd")
    res = router.dispatch(cmd)
    assert res.type == "error"
    assert "Unknown command" in res.content


def test_handle_help():
    router = SlashCommandRouter()
    cmd = router.parse("/help")
    res = router.dispatch(cmd)
    assert res.type == "text"
    assert "Available commands" in res.content
    assert "/help" in res.content


def test_handle_clear():
    router = SlashCommandRouter()
    cmd = router.parse("/clear")
    res = router.dispatch(cmd)
    assert res.type == "toast"
    assert res.toast_message == "Chat history cleared"


def test_handle_ask():
    router = SlashCommandRouter()
    cmd = router.parse("/ask")
    res = router.dispatch(cmd)
    assert res.type == "error"
    assert "Please provide a question" in res.content

    cmd = router.parse("/ask what is this?")
    res = router.dispatch(cmd)
    assert res.type == "stream"
    assert res.content == "what is this?"
