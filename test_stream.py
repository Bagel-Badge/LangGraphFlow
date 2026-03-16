import time
from openai import OpenAI

client = OpenAI(
    base_url="https://gcli.ggchan.dev/v1",
    api_key="gg-gcli-x0kIRzt1-pK9u4jr91etVXdAKb_5WLZ2VC7RHTtmFF8"
)

start_time = time.time()
first_chunk_time = None

print("=== Starting Stream Test ===")
print("Sending request...")
response = client.chat.completions.create(
    model="gemini-3.1-pro-preview",
    messages=[{"role": "user", "content": "你是什么模型？"}],
    stream=True
)

print("Receiving chunks...")
full_content = ""
for i, chunk in enumerate(response):
    if first_chunk_time is None:
        first_chunk_time = time.time()
        print(f"\n[Time to first chunk (TTFT): {first_chunk_time - start_time:.4f} seconds]")
    
    # Just print the first 5 chunks to see the structure
    if i < 5:
        print(f"\n--- Chunk {i} ---")
        if chunk.choices:
            choice = chunk.choices[0]
            print(f"delta structure: {choice.delta.model_dump()}")
            content = choice.delta.content
            print(f"delta content: {repr(content)}")
            if content:
                full_content += content
    else:
        if chunk.choices and chunk.choices[0].delta.content:
            full_content += chunk.choices[0].delta.content

print(f"\nTotal time: {time.time() - start_time:.4f} seconds")
print(f"Full response: {full_content}")
