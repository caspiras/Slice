"""Skill loader and parser for Slice IDE."""

import os
from pathlib import Path
from typing import Dict, List, Optional
import re


class Skill:
    """Represents a single skill with its metadata and instructions."""

    def __init__(self, name: str, description: str, instructions: str, metadata: Dict = None):
        self.name = name
        self.description = description
        self.instructions = instructions
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Skill(name='{self.name}', description='{self.description}')"


class SkillLoader:
    """Loads and manages skills from the slice-skills/ directory."""

    SKILLS_DIR = "slice-skills"

    def __init__(self, working_directory: str):
        self.working_directory = working_directory
        self.skills: Dict[str, Skill] = {}

    def load_skills(self) -> Dict[str, Skill]:
        """
        Load all skills from the slice-skills/ directory.
        Returns a dict mapping skill names to Skill objects.
        """
        skills_path = Path(self.working_directory) / self.SKILLS_DIR

        # If directory doesn't exist, return empty dict (no error)
        if not skills_path.exists() or not skills_path.is_dir():
            return {}

        # Find all .md files in the skills directory
        skill_files = list(skills_path.glob("*.md"))

        # Filter out README and other documentation files
        excluded_files = {'README.md', 'CHANGELOG.md', 'LICENSE.md'}
        skill_files = [f for f in skill_files if f.name not in excluded_files]

        for skill_file in skill_files:
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    # Use the name from frontmatter as the key
                    self.skills[skill.name] = skill
            except Exception as e:
                # Log error but continue loading other skills
                print(f"Warning: Failed to load skill from {skill_file.name}: {e}")

        return self.skills

    def _parse_skill_file(self, file_path: Path) -> Optional[Skill]:
        """
        Parse a single skill file with frontmatter.

        Expected format:
        ---
        name: skill-name
        description: Brief description
        other_field: value
        ---

        # Instructions
        The actual instructions go here...
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            raise ValueError(f"Could not read file: {e}")

        # Parse frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)

        if not frontmatter_match:
            raise ValueError("File does not contain valid frontmatter (---...---)")

        frontmatter_text = frontmatter_match.group(1)
        instructions = frontmatter_match.group(2).strip()

        # Parse frontmatter fields
        metadata = {}
        name = None
        description = None

        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if not line or ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if key == 'name':
                name = value
            elif key == 'description':
                description = value
            else:
                metadata[key] = value

        # Validate required fields
        if not name:
            raise ValueError("Skill file missing required 'name' field in frontmatter")
        if not description:
            raise ValueError("Skill file missing required 'description' field in frontmatter")
        if not instructions:
            raise ValueError("Skill file has no instructions after frontmatter")

        return Skill(name=name, description=description, instructions=instructions, metadata=metadata)

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def has_skills(self) -> bool:
        """Check if any skills are loaded."""
        return len(self.skills) > 0

    def list_skill_names(self) -> List[str]:
        """Get a list of all loaded skill names."""
        return list(self.skills.keys())
