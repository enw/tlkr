# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a reference repository for DeepSeek OCR usage patterns and examples. It documents how to use the DeepSeek OCR model through Ollama for various OCR and document processing tasks.

## Key Files

- **prompt_examples.md**: Contains prompt patterns for different OCR use cases (document conversion, image OCR, figure parsing, etc.)
- **shell_examples.md**: Contains shell command examples showing how to invoke DeepSeek OCR via Ollama CLI
- **enw_resume.md**: Currently empty, appears to be reserved for future content

## DeepSeek OCR Usage Patterns

The repository documents several OCR prompt patterns:

1. **Document Conversion**: `<image>\n<|grounding|>Convert the document to markdown.`
2. **General OCR**: `<image>\n<|grounding|>OCR this image.`
3. **Layout-free OCR**: `<image>\nFree OCR.`
4. **Figure Parsing**: `<image>\nParse the figure.`
5. **Image Description**: `<image>\nDescribe this image in detail.`
6. **Object Recognition**: `<image>\nLocate <|ref|>xxxx<|/ref|> in the image.`

## Running DeepSeek OCR

Commands use the Ollama CLI with the format:
```bash
ollama run deepseek-ocr "<image_path>\n<|grounding|>Prompt text."
```

The `<|grounding|>` token is key for document-focused OCR tasks. For general image description, it can be omitted.

## Notes

- This is a documentation repository, not a code project
- No build, test, or development commands are needed
- When adding new examples, follow the existing pattern structure in the respective markdown files
