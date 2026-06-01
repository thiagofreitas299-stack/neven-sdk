# Contributing to NEVEN TECH

Thank you for your interest in contributing to **NEVEN TECH — The Physical World Runtime**! We are building the foundational software layer that connects AI agents to physical infrastructure at scale, and your contributions are vital to achieving this goal.

---

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful, welcoming, and professional in all interactions.
- Focus on what is best for the community and the project.
- Accept constructive criticism gracefully.
- Show empathy and consideration toward other contributors.

---

## How Can I Contribute?

### 1. Reporting Bugs
If you find a bug, please open an issue on our GitHub repository. Include:
- A clear, descriptive title.
- Steps to reproduce the issue.
- Expected vs. actual behavior.
- System environment details (OS, Python version, library versions).
- Relevant log output or error traces.

### 2. Suggesting Enhancements
We are always looking for ways to improve NEVEN. If you have an idea for a new feature:
- Search existing issues to ensure it hasn't been proposed yet.
- Open an issue outlining the feature, its use case, and potential implementation details.

### 3. Submitting Pull Requests
We welcome code contributions via Pull Requests (PRs). Please follow these steps:

1. **Fork the repository** and create a new branch from `main`:
   ```bash
   git checkout -b feature/my-amazing-feature
   ```

2. **Set up your development environment**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Write clean, documented code**:
   - Follow PEP 8 guidelines for Python code.
   - Use type hints for all function signatures.
   - Document new classes, methods, and modules with docstrings.

4. **Ensure all tests pass**:
   ```bash
   pytest
   ```

5. **Format and lint your code**:
   We use `black` for formatting and `ruff` for linting.
   ```bash
   black neven/ tests/
   ruff check neven/ tests/
   ```

6. **Commit your changes** using descriptive commit messages following Conventional Commits (e.g., `feat: add MQTT protocol driver`, `fix: resolve memory leak in tracker`).

7. **Push to your fork** and open a Pull Request to the `main` branch of the official repository.

---

## Code Architecture Guidelines

When adding new features, please adhere to our architectural design principles:

- **Separation of Concerns**: Keep perception algorithms, safety logic, state tracking, and protocol drivers isolated.
- **Safety First**: Any physical actuation MUST go through the `DeterministicSafetyEngine` (DSE). Never bypass the safety verification pass.
- **Asynchronous & Real-time**: Optimize for high-throughput, low-latency execution. Use asynchronous programming where appropriate, especially in the API and event streaming layers.
- **Platform Agnostic**: Ensure that drivers and core systems remain platform-agnostic, running seamlessly across local machines, edge devices, and cloud-hosted environments.

---

## Contact & Support

If you have questions or need assistance, feel free to reach out to the engineering team at [engineering@neventech.com](mailto:engineering@neventech.com).

Thank you for contributing to the future of physical AI!
