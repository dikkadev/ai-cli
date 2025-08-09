from dataclasses import dataclass
from pydantic import BaseModel

from llm.provider import Provider, ProviderResponse


class Answer(BaseModel):
    text: str


@dataclass
class FakeProvider(Provider):
    value: str

    def generate_structured(self, *, prompt: str, response_model: type[Answer]) -> ProviderResponse[Answer]:
        return ProviderResponse(output=response_model(text=self.value), raw={"prompt": prompt}, model="fake")


def test_fake_provider_roundtrip():
    provider = FakeProvider(value="hello")
    result = provider.generate_structured(prompt="hi", response_model=Answer)
    assert result.output.text == "hello"
    assert result.model == "fake"
    assert "prompt" in result.raw
