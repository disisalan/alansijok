import os
import requests
from google import genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv() # Loads variables from .env file (for GEMINI_API_KEY)

def fetch_and_clean_content(url: str) -> str | None:
    """
    Fetches the content of a webpage and cleans it to extract plain text.
    """
    print(f"Fetching content from: {url}...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        print(f"Error: Unable to fetch webpage. {e}")
        return None

    print("Cleaning HTML...")
    soup = BeautifulSoup(response.text, 'html.parser')

    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()

    paragraphs = soup.find_all('p')
    
    if not paragraphs:
        print("Warning: No <p> tags found. Falling back to all text.")
        cleaned_text = soup.body.get_text(separator=' ', strip=True)
    else:
        cleaned_text = ' '.join(p.get_text(strip=True) for p in paragraphs)

    cleaned_text = ' '.join(cleaned_text.split())
    
    print(f"Cleaning complete. Content length: {len(cleaned_text)} characters.")
    return cleaned_text

def get_summary_from_gemini(content: str, api_key: str) -> str:
    """
    Sends the cleaned content to the Gemini API using the genai.Client() method.
    """
    if not content:
        return "Error: Content to summarize is empty."

    print("Connecting to Gemini API using genai.Client()...")
    
    # --- Your Custom Prompt ---
    prompt_template = f"""
    Analyze the following webpage content and perform two tasks:
    1.  First give me 3-5 strong bullet points for the information presented. It should be structured for easy reading, understanding, and addition of value to the user
    2.  Add one short, single-line insight that helps user understand the overall context and a conclusion of the overall text.

    You MUST display the output in the following structure, and only this structure:

    Summary:
    • <point 1>
    • <point 2>
    • <point 3>
    • <point 4>
    • <point 5>
    Insight:
    <single-line insight>

    ---
    WEBPAGE CONTENT:
    {content}
    ---
    """

    try:
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_template
        )
        return response.text.strip()
        
    except Exception as e:
        return f"An error during Gemini API call: {e}"

# --- Main execution block ---
if __name__ == "__main__":
    # 1. Get API Key from environment variable
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("Error: 'GEMINI_API_KEY' environment variable not set.")
    else:
        # 2. Set the target URL
        url_to_summarize = "https://en.wikipedia.org/wiki/Artificial_intelligence"

        # 3. Fetch and clean the content
        cleaned_content = fetch_and_clean_content(url_to_summarize)

        if cleaned_content:
            # 4. Pass to Gemini and print the result
            summary_output = get_summary_from_gemini(cleaned_content, GEMINI_API_KEY)
            
            print("\n--- SCRIPT OUTPUT ---")
            print(summary_output)
            print("---------------------")

            # --- New code to write output to file ---
            output_filename = "summary_output.txt"
            print(f"Writing output to {output_filename}...")
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(summary_output)
                print("Successfully wrote summary to file.")
            except IOError as e:
                print(f"Error: Unable to write to file {output_filename}. {e}")
            # --- End of new code ---