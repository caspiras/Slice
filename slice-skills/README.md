# Slice Skills

This directory contains skill files for Slice. Skills are custom commands that provide the AI with specific instructions for common tasks.

## What are Skills?

Skills are predefined instruction sets that you can invoke with slash commands (e.g., `/test`, `/hello`). When you invoke a skill, Slice loads the instructions and feeds them to the AI model, guiding it to perform specific tasks.

## How to Use Skills

1. **Place skill files in this directory** (`slice-skills/`)
2. **Name them with `.md` extension** (e.g., `my-skill.md`)
3. **Invoke them in Slice** by typing `/skill-name`

## Skill File Format

Each skill file must follow this format:

```markdown
---
name: skill-name
description: Brief description of what this skill does
---

# Skill Instructions

Detailed instructions for the AI model go here.

When this skill is invoked:
1. Do step one
2. Do step two
3. etc.
```

### Required Fields

- **name**: The command name (you'll type `/name` to invoke it)
- **description**: A brief one-line description
- **Instructions**: Everything after the `---` markers

### Optional Fields

You can add custom metadata in the frontmatter:

```markdown
---
name: deploy
description: Deploy the application
author: Your Name
version: 1.0
---
```

## Example Skills

### Simple Greeting Skill

**File:** `hello.md`

```markdown
---
name: hello
description: Say hello and show system info
---

# Hello Skill

When invoked:
1. Greet the user warmly
2. Show the current date with `date` command
3. Display the username with `whoami`
4. End with a friendly message
```

Invoke with: `/hello`

### Git Status Skill

**File:** `git-status.md`

```markdown
---
name: status
description: Show git repository status
---

# Git Status Skill

When invoked:
1. Run `git status`
2. Run `git log --oneline -5`
3. Summarize the repository state
```

Invoke with: `/status`

## Tips for Writing Skills

1. **Be specific**: Give clear, step-by-step instructions
2. **Use tool names**: Reference the bash tool explicitly when needed
3. **Keep it focused**: One skill should do one thing well
4. **Test with your model**: Different Ollama models may interpret instructions differently

## Built-in Examples

This directory includes three example skills:

- `/test` - Simple test to verify skills work
- `/hello` - Greeting with system information
- `/status` - Git repository status check

Feel free to modify or delete these examples!

## Troubleshooting

**Skill not loading?**
- Check that the file has `.md` extension
- Verify the frontmatter is properly formatted with `---` markers
- Ensure both `name` and `description` fields are present

**Skill not working as expected?**
- Some Ollama models follow instructions better than others
- Try making the instructions more explicit
- Test with different models (gemma4, mistral, llama3.1)

## Advanced Usage

Skills can reference Slice's built-in tools:

- **bash tool**: For running commands
- **read_document tool**: For reading files
- **write_document tool**: For writing documents
- **edit_code tool**: For editing code with diffs

Example:

```markdown
---
name: analyze
description: Analyze project structure
---

When invoked:
1. Use the bash tool to run `find . -name "*.py" | head -20`
2. Read the README.md file using read_document
3. Summarize the project structure
```
