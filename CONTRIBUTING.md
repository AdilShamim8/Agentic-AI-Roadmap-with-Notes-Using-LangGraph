# Contributing to Agentic AI Roadmap with Notes Using LangGraph

First off, thank you for considering contributing to the Agentic AI Roadmap! 
It's people like you who make this resource valuable for the global AI community.

This document provides guidelines and instructions for contributing to this project.  Following these guidelines helps communicate that you respect the time of the developers managing and developing this open-source project.  In return, we will respect your efforts. 

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Contributing Content](#contributing-content)
  - [Pull Requests](#pull-requests)
- [Styleguides](#styleguides)
  - [Git Commit Messages](#git-commit-messages)
  - [Markdown Styleguide](#markdown-styleguide)
  - [Code Examples Styleguide](#code-examples-styleguide)
  - [LangGraph-Specific Guidelines](#langgraph-specific-guidelines)
- [Review Process](#review-process)
- [Community](#community)
- [Attribution](#attribution)

---

## Code of Conduct

This project and everyone participating in it are governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [adil.shamim. dev@example.com](mailto:adil.shamim.dev@example.com).

---

## How Can I Contribute? 

### Reporting Bugs

Before creating bug reports, please check [the issue list](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-Using-LangGraph/issues) to see if the issue has already been reported.

When filing a bug report, please include: 

- **A clear and descriptive title** for the issue
- **The exact steps to reproduce the problem** in as much detail as possible
- **Specific examples** to demonstrate the steps (code snippets, screenshots, etc.)
- **The behavior you observed** after following the steps
- **The behavior you expected to see instead** and why
- **Screenshots or logs** if applicable
- **Your configuration and environment** (Python version, LangGraph/LangChain version, OS, etc.)

### Suggesting Enhancements

Enhancement suggestions are always welcome! When proposing an enhancement, please:

- **Use a clear and descriptive title** for the issue
- **Provide a step-by-step description of the suggested enhancement** in as much detail as possible
- **Provide specific examples** to demonstrate the steps or intended behavior
- **Describe the current behavior and explain what you expected to see instead**
- **Explain why this enhancement would be useful** for learners and practitioners

### Contributing Content

Content contributions are the heart of this project! Here's how to contribute new content or improve existing content:

#### For New Topics or Examples

- Check if the topic fits within the roadmap structure (e.g., LangGraph agents, memory, multi-agent, production, etc.)
- Create an issue first to discuss the proposed content
- Follow the repository structure when adding new files
- Provide clear, runnable code examples with comments

#### For Improvements to Existing Content

- Ensure corrections are accurate and up-to-date (especially for LangGraph APIs, which evolve rapidly)
- Maintain the existing format and style
- Add references to official documentation or research papers where appropriate

#### Types of Contributions We Love

-  New notes or tutorials on agentic AI topics
-  Working LangGraph code examples (agents, multi-agent workflows, memory graphs, etc.)
-  Curated resources (articles, papers, courses)
-  Bug fixes and documentation improvements
-  Translations and accessibility improvements

### Pull Requests

When submitting a pull request:

1. **Fork the repository** and create your branch from `main`
2. **Follow the structure** of the repository for new files
3. **Include relevant tests** if applicable (especially for code examples)
4. **Ensure code quality** through clear documentation and comments
5. **Update documentation** if your changes affect the README, roadmap, or any guides
6. **Issue the pull request** with a clear title and description

---

## Styleguides

### Git Commit Messages

- Use the present tense ("Add feature", not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or fewer
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  -  `:memo:` when adding or updating documentation
  -  `:bug:` when fixing a bug
  -  `:sparkles:` when adding a new feature
  -  `:recycle:` when refactoring code
  -  `:white_check_mark:` when adding tests
  -  `:robot:` when adding/updating agent examples

### Markdown Styleguide

- Use consistent headings and nested headings
- Use backticks for inline code references (e.g., `StateGraph`, `add_node`)
- Use proper code blocks with language specification (```python)
- Include blank lines between sections for readability
- Use descriptive link text rather than "click here" or similar phrases
- For complex agent workflows, include diagrams or flowcharts if possible

### Code Examples Styleguide

- Include clear, concise comments
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide for Python code
- Include docstrings for functions and classes
- Provide example outputs where relevant
- Keep examples focused on demonstrating one concept at a time
- Ensure code can be run with the dependencies listed in `requirements.txt`
- Avoid hardcoding secrets/API keys—use environment variables

### LangGraph-Specific Guidelines

- Use the latest stable LangGraph API (document the version if needed)
- Define agent state clearly using dataclasses or TypedDicts
- Name nodes and edges descriptively (e.g., `planner`, `executor`, `should_continue`)
- Document the flow of your graph with comments or diagrams
- When using tools, clearly define their purpose and expected input/output
- For multi-agent examples, explain the role of each agent in the workflow

---

## Review Process

The maintainers will review your pull request and may suggest changes or improvements. The review process includes:

1. Checking if the contribution fits the project scope
2. Verifying technical accuracy (especially for LangGraph/LangChain APIs)
3. Checking content quality and clarity
4. Testing code examples, if applicable
5. Ensuring compatibility with the latest LangGraph version

Once approved, your contributions will be merged into the main branch.

---

## Community

Feel free to join discussions in the [issues section](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-Using-LangGraph/issues).  
We value respectful, constructive, and inclusive communication.

---

## Attribution

This Contributing Guide is adapted from the [Atom Contributing Guide](https://github.com/atom/atom/blob/master/CONTRIBUTING.md) and [GenAI Roadmap with LangChain](https://github.com/AdilShamim8/GenAI-Roadmap-with-Notes-Using-LangChain).

---

<div align="center">

Thank you for contributing to the Agentic AI Roadmap!  
Your efforts help make AI education more accessible to everyone. 

</div>
