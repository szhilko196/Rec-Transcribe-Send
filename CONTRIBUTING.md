# Contributing to Meeting Transcriber

Thank you for considering contributing to Meeting Transcriber! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Docker version, etc.)
- Console logs if applicable

### Suggesting Features

We love feature suggestions! Please create an issue with:
- Clear description of the feature
- Use case and benefits
- Possible implementation approach (optional)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow existing code style
   - Add tests if applicable
   - Update documentation
4. **Commit your changes**
   ```bash
   git commit -m "Add feature: your feature description"
   ```
5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request**

### Development Setup

1. Clone the repository
2. Install dependencies
3. Set up `.env` file
4. Run `docker-compose up -d`
5. Test your changes

### Code Style

- **Python**: Follow PEP 8
- **JavaScript**: Use ES6+ syntax
- **Comments**: Write clear, concise comments
- **Documentation**: Update README.md if needed

### Testing

Before submitting a PR:
- Test with sample video files
- Check Docker containers are running
- Verify all services respond correctly
- Test end-to-end pipeline

## Questions?

Feel free to open an issue or discussion on GitHub!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
