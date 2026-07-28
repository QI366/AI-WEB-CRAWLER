import json

import anthropic

from config import settings

client = anthropic.Anthropic()

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string", "description": "2-3 sentence summary of the page"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main takeaways as short bullet points",
        },
        "topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Relevant topic tags for the page",
        },
    },
    "required": ["title", "summary", "key_points", "topics"],
    "additionalProperties": False,
}


def extract_structured_data(page_text: str) -> dict:
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        output_config={
            "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
            "effort": "low",
        },
        messages=[
            {
                "role": "user",
                "content": (
                    "Read the following web page content and extract structured "
                    "information about it.\n\n---\n\n" + page_text
                ),
            }
        ],
    )

    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)
