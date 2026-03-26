# Enhanced Learning Workflow

## Overview
This workflow describes how the Homeschool assistant helps you process class notes to create effective learning materials. The workflow has been refined to be more manual and controllable, giving you full oversight of the learning material generation process.

## Workflow Steps

### 1. Note Taking
- Take your notes for each class using Obsidian or your preferred note-taking app
- Use consistent formatting for better processing results
- Mark questions using `???` notation for single-line or `?\*\*?` for multi-line questions

### 2. Manual Processing Trigger
When you finish your notes and want to generate learning materials:
```bash
python -m homeschool sync
```

This initiates a manual sync process that you control completely.

### 3. Generated Learning Materials
After running the sync command, the assistant will generate:

#### A. Anki Flashcards
- Created from your lecture notes
- Added to the appropriate class deck in Anki
- Available in multiple formats:
  - **Cloze deletion** (primary format for concept reinforcement)
  - **Image occlusion** (when applicable, with image links provided)
  - **Multiple choice questions** (for factual recall)

*Note: Flashcard creation requires manual confirmation in Anki due to platform limitations*

#### B. Short Answer Review Questions
- Generated from your notes
- Titled similarly to the source note
- Stored in a 'Review Questions' folder for each class
- Designed for active recall practice

#### C. Concept Summaries & Extensions
- Page-by-page summary generation
- Concept expansion for topics touched on but not deeply covered
- Added to new or expanded sections in your notes

#### D. Question Answering
- Answers to questions you've marked in your notes
- Added directly to where the questions appear
- Can use local ML models for privacy-sensitive content

### 4. Review & Feedback Loop
After receiving generated materials:
1. **Review flashcards** in Anki as usual
2. **Answer short answer questions** (handwritten or typed)
3. **If using images**: Take pictures of handwritten answers for processing
4. **Get feedback**: The assistant reviews your responses and provides constructive feedback
5. **Daily review**: End-of-day review of challenging concepts for next-day preparation

## Tools & Configuration

### Required Setup
- **Obsidian**: For note taking (or any markdown-compatible app)
- **Anki**: For spaced repetition flashcard review
- **Homeschool**: For processing and material generation
- **Local LLM** (Optional): For privacy-sensitive operations via Jan AI + Continue

### Configuration Options
Adjust in `config.yaml`:
- Flashcard types and formats
- Review question generation sensitivity
- Summary depth and length
- Local model selection for private operations

## Error Handling & Troubleshooting

### Common Issues
- **Sync fails**: Check Docker is running and config.yaml paths are correct
- **No materials generated**: Verify note formatting and question markers
- **Anki integration**: Manual confirmation required due to platform security
- **Processing slow**: Consider model selection or hardware acceleration options

### Recovery Procedures
- Failed syncs can be retried safely
- No partial state is left behind
- Configuration errors provide clear guidance
- Logs available via `python -m homeschool logs` (future enhancement)

## Best Practices

1. **Consistent Formatting**: Use standard markdown and question notation
2. **Regular Processing**: Sync after each study session for best results
3. **Active Review**: Engage with generated materials rather than passive consumption
4. **Feedback Utilization**: Use assistant feedback to improve note-taking and understanding
5. **Privacy Awareness**: Use local models for sensitive information

## Integration with Local AI Workflow
This learning workflow complements the Local AI Workflow by:
- Using the same local inference infrastructure (Jan AI)
- Leveraging the vector database (ChromaDB) for context
- Benefiting from the privacy-focused setup
- Sharing the same easy-to-use manual trigger mechanism