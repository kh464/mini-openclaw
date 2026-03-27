"""Scans skills/ directory and generates SKILLS_SNAPSHOT.md."""

import re
from pathlib import Path


def scan_skills(skills_dir: str | Path) -> list[dict]:
    """Scan skills directory, parse YAML frontmatter, return list of skill metadata."""
    skills = []
    skills_path = Path(skills_dir)
    if not skills_path.is_dir():
        return skills

    for skill_md in sorted(skills_path.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        if meta:
            meta["location"] = f"./skills/{skill_md.parent.name}/SKILL.md"
            skills.append(meta)
    return skills


def _parse_frontmatter(text: str) -> dict | None:
    """Parse frontmatter from SKILL.md file. Returns a dict or None."""
    # 匹配 "---" 开头和结尾的文本块
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    result = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
    return result


def generate_snapshot(skills: list[dict]) -> str:
    """Generate SKILLS_SNAPSHOT.md content."""
    lines = ["<available_skills>"]
    for s in skills:
        lines.append("  <skill>")
        lines.append(f"    <name>{s.get('name', 'unknown')}</name>")
        lines.append(f"    <description>{s.get('description', '')}</description>")
        lines.append(f"    <location>{s.get('location', '')}</location>")
        lines.append("  </skill>")
    lines.append("</available_skills>")
    return "\n".join(lines)

# 添加详细注释，说明函数参数和返回值
def write_snapshot(base_dir: str | Path) -> str:
    """Scan skills and write SKILLS_SNAPSHOT.md. Returns the content."""
    base = Path(base_dir)
    skills = scan_skills(base / "skills")
    content = generate_snapshot(skills)
    (base / "SKILLS_SNAPSHOT.md").write_text(content, encoding="utf-8")
    return content
