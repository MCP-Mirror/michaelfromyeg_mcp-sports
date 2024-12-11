# MCP NHL

An MCP server to getting NHL data.

Connect to this server via.

```jsonc
// MacOS
{
    "mcpServers": {
        "nhl": {
            "command": "uv",
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/PARENT/FOLDER/nhl",
                "run",
                "nhl"
            ]
        }
    }
}
// Windows
{
    "mcpServers": {
        "nhl": {
            "command": "uv",
            "args": [
                "--directory",
                "C:\\ABSOLUTE\PATH\TO\PARENT\FOLDER\nhl",
                "run",
                "nhl"
            ]
        }
    }
}
```
