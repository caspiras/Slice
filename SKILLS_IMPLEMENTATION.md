# Skills Feature Implementation

## Overview

This document describes the skills feature implementation for Slice, enabling users to create custom slash commands with predefined instructions for the AI model.

## Implementation Summary

### Files Created

1. **`src/slice/skills.py`** (120 lines)
   - `Skill` class: Represents a single skill
   - `SkillLoader` class: Loads and manages skills from `slice-skills/` directory
   - Parses frontmatter and instructions
   - Handles errors gracefully

2. **`slice-skills/` directory**
   - Contains skill files (`.md` format)
   - Example skills provided: `/test`, `/hello`, `/status`
   - README.md with documentation

### Files Modified

1. **`src/slice/main.py`**
   - Added skill loader import
   - Loads skills on startup
   - Displays loaded skills to user
   - Passes skill_loader to ChatSession

2. **`src/slice/chat.py`**
   - Added skill_loader parameter to `__init__`
   - Detects slash commands in user input
   - Injects skill instructions into conversation history
   - Handles invalid skill commands gracefully

3. **`src/slice/ui.py`**
   - Shows available skills on startup
   - Lists skill names in help text

## How It Works

### Skill File Format

```markdown
---
name: skill-name
description: Brief description
---

# Instructions for the AI

Step-by-step instructions go here...
```

### Flow

1. **Startup**: Slice loads all `.md` files from `slice-skills/`
2. **Display**: Shows loaded skills to user
3. **Detection**: When user types `/skill-name`, Slice detects it
4. **Injection**: Skill instructions are added to conversation history
5. **Execution**: Ollama model receives and follows the instructions

### Key Design Decisions

1. **Directory**: `slice-skills/` (not `.slice/`) to avoid hidden folder confusion
2. **Optional**: No error if directory doesn't exist
3. **Flexible**: Any `.md` filename works (name comes from frontmatter)
4. **Safe**: Invalid skill files are skipped with a warning
5. **Model-agnostic**: Works with any Ollama model

## Testing

All tests passed:

- ✓ Imports work correctly
- ✓ Skills load from directory
- ✓ Empty directory handled gracefully
- ✓ Invalid skill files skipped safely
- ✓ Command detection works
- ✓ Skill retrieval accurate
- ✓ No syntax errors

## Usage Example

1. Create `slice-skills/deploy.md`:
```markdown
---
name: deploy
description: Deploy the application
---

When invoked:
1. Run tests with `pytest`
2. Build with `npm run build`
3. Deploy with `./deploy.sh`
```

2. Run Slice:
```bash
$ slice
✓ Loaded 1 skill(s): /deploy
```

3. Use the skill:
```
🍕 /deploy
```

## Features

- ✅ Custom slash commands
- ✅ Frontmatter parsing
- ✅ Error handling
- ✅ Help text integration
- ✅ Example skills included
- ✅ Full documentation
- ✅ No dependencies added
- ✅ Backwards compatible

## Code Quality

- Clean separation of concerns
- Comprehensive error handling
- Clear documentation
- Type hints where appropriate
- Follows existing code style
- No breaking changes

## Future Enhancements (Not Implemented)

Potential improvements for later:

- Skill arguments support (`/deploy production`)
- Skill aliases
- Skill categories/tags
- Global skills from `~/.slice/skills/`
- Skill templates
- Skill validation on load

## Files Changed

```
src/slice/
  ├── skills.py          (NEW - 120 lines)
  ├── main.py            (MODIFIED - +13 lines)
  ├── chat.py            (MODIFIED - +41 lines)
  └── ui.py              (MODIFIED - +6 lines)

slice-skills/
  ├── README.md          (NEW - documentation)
  ├── test-skill.md      (NEW - example)
  ├── hello.md           (NEW - example)
  └── git-status.md      (NEW - example)
```

## Verification

Run these commands to verify:

```bash
# Test imports
python3 -c "from src.slice.skills import SkillLoader"

# Test loading
python3 -c "
from src.slice.skills import SkillLoader
import os
loader = SkillLoader(os.getcwd())
skills = loader.load_skills()
print(f'Loaded {len(skills)} skills')
"

# Test startup
slice  # Then Ctrl+C to exit
```

## Conclusion

The skills feature is fully implemented, tested, and documented. It integrates seamlessly with Slice's existing architecture and provides a flexible way for users to extend Slice's functionality through custom commands.
