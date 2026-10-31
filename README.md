# claude-plugins

Claude Code plugins I built for my own work and use day to day.

| Plugin | What it does |
|---|---|
| **serbia-job-search** | MCP server for [Infostud](https://poslovi.infostud.com) and [HelloWorld.rs](https://www.helloworld.rs) ([poslovi-mcp](https://github.com/umilutinovic25-hash/poslovi-mcp)) plus a skill that sources jobs broadly, verifies seniority/location/legitimacy on the full posting, and only applies after explicit approval. |
| **llm-agent-hardening** | Skill for hardening web apps that call an LLM or run an agent tool loop: the boundaries reviewers usually miss, how to prove each control with tests, a footgun scanner and a baseline-compare script. |
| **social-video-recut** | Skill + Python/ffmpeg pipeline that turns a long landscape video into a 1:1 or 9:16 social edit: scene detection, dialogue stem split, face-tracked crop, transitions and burned-in word-level captions, with a QA pass. |

## Install

```
/plugin marketplace add umilutinovic25-hash/claude-plugins
/plugin install serbia-job-search@uros-plugins
/plugin install llm-agent-hardening@uros-plugins
/plugin install social-video-recut@uros-plugins
```

## Requirements

- **serbia-job-search:** [uv](https://docs.astral.sh/uv/) (`uvx` runs the MCP server). On first use the skill asks for your profile and saves it to `~/.config/serbia-job-search/profile.md`.
- **llm-agent-hardening:** bash.
- **social-video-recut:** macOS or Linux, ffmpeg, Python 3.12 with uv, yt-dlp (installed by `setup.sh` if missing). Speaker-stem separation uses Demucs.

## License

MIT, see [LICENSE](LICENSE). Bundled third-party assets are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
