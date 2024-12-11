# MCP NHL

An MCP server to getting NHL data.

Connect to this server via.

```jsonc
// MacOS
{
    "mcpServers": {
        "weather": {
            "command": "uv",
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather",
                "run",
                "weather"
            ]
        }
    }
}
// Windows
{
    "mcpServers": {
        "weather": {
            "command": "uv",
            "args": [
                "--directory",
                "C:\\ABSOLUTE\PATH\TO\PARENT\FOLDER\weather",
                "run",
                "weather"
            ]
        }
    }
}
```
