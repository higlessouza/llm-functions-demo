from openai import OpenAI
import os
from openai.types.chat.chat_completion_content_part_image_param import (
    ChatCompletionContentPartImageParam,
    ImageURL,
)
from openai.types.chat.chat_completion_content_part_text_param import (
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_message_param import (
    ChatCompletionUserMessageParam
)
api_key = os.getenv("OPENAI_API_KEY")

class OpenAiService:
    def __init__(self):
        self.client = OpenAI(api_key=api_key)

    def get_embedding(self, text):
        embedding = self.client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )
        vector_embedding = embedding.data[0].embedding
        return vector_embedding

    def get_image_context(self, imagem_base64: str) -> str:
        # open ai image object
        image = ImageURL(url=f"data:image/jpeg;base64,{imagem_base64}")
        image_content = ChatCompletionContentPartImageParam(
            type="image_url", image_url=image
        )

        # open ai text object
        text_content = ChatCompletionContentPartTextParam(
            type="text", text="Você é um agente extrator de capchas, voce vai analisar a imagem e me retornar APENAS o texto do capcha e nada mais."
        )

        # open ai message
        message = ChatCompletionUserMessageParam(
            role="user",
            content=[image_content, text_content],
        )

        # open ai response
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[message],
        )

        text_answer = response.choices[0].message.content
        return text_answer