import logging
import os
import psycopg
from psycopg.rows import dict_row
from diskcache import Cache
from gradio_client import Client
from groq import Groq
import chromadb
import ollama
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
import google.generativeai as genai


# Setup logging with rotation
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
handler = RotatingFileHandler('ai_client.log', maxBytes=10485760, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# POSTGRESQL PARAMETERS
DB_PARAMS = {
    'dbname': os.getenv('DB_NAME', 'memory_agent'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

@contextmanager
def connect_db():
    """Context manager for database connection."""
    conn = None
    try:
        conn = psycopg.connect(**DB_PARAMS)
        yield conn
    except psycopg.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def fetch_conversations():
    """Fetch conversations from the database."""
    try:
        with connect_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute('SELECT * FROM conversations')
                return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return []

def store_conversations(prompt, response):
    """Store a conversation in the database."""
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO conversations (timestamp, prompt, response) VALUES (CURRENT_TIMESTAMP, %s, %s)',
                    (prompt, response)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"Error storing conversation: {e}")

def pure_llama3(conv):
    # Usar Gemini como primário
    if gemini_model:
        try:
            prompt = conv if isinstance(conv, str) else "\n".join([m.get("content", "") for m in conv])
            response = gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini error in pure_llama3: {e}")
    
    # Fallback: Groq
    client_groq = Groq(api_key=GROQ_API)
    if isinstance(conv, str):
        conv = [{"role": "user", "content": conv}]
    response = client_groq.chat.completions.create(messages=conv, model=MODEL_LLM)
    return response.choices[0].message.content

# Constants from environment variables with defaults
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_BASE_DIR, '..', '..'))
CACHE_DIR = os.getenv('CACHE_DIR', os.path.join(_PROJECT_ROOT, 'Cache'))
MODEL_LLM = os.getenv('MODEL_LLM', 'llama-3.1-8b-instant')
MODEL_EMBED = os.getenv('MODEL_EMBED', 'nomic-embed-text')
GROQ_API = os.getenv("GROQ_API")
VECTOR_DB_NAME = 'conversations'

# Initialize components
cache = Cache(CACHE_DIR)
try:
    client = Client("osanseviero/mistral-super-fast")
except Exception as e:
    logger.error(f"Failed to connect to Gradio Mistral Space: {e}")
    client = None
chromadb_client = chromadb.Client()

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_model = None
# Gemini desativado temporariamente - as chaves fornecidas não têm cota (Free tier limit: 0)
# if GEMINI_API_KEY:
#     try:
#         genai.configure(api_key=GEMINI_API_KEY)
#         gemini_model = genai.GenerativeModel('gemini-2.0-flash')
#         logger.info("Gemini initialized successfully as primary LLM.")
#     except Exception as e:
#         logger.error(f"Failed to initialize Gemini: {e}")
#         gemini_model = None

messages_normal = [
    {"role": "system", "content": "You are named JARVIS, inspired by Iron Man, brought to life by Likhith Sai"},
    {"role": "system", "content": "You can do anything on a laptop."},
    {"role": "system", "content": "You follow instructions from your user. Very Important"},
    {"role": "system", "content": "If you need any real-time information or anything else, the system provides"}
]

class AIClient:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API)

    def safe_predict(self, prompt):
        """Predict response using Gemini (primary) or Groq (fallback) with caching."""
        if prompt in cache and cache[prompt] is not None:
            return cache[prompt]

        try:
            # Primary: Gemini
            if gemini_model:
                response = gemini_model.generate_content(prompt)
                result = response.text.strip()
            else:
                # Fallback: Groq
                response = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=MODEL_LLM,
                    max_tokens=256,
                    temperature=0.9,
                    top_p=0.9
                )
                result = response.choices[0].message.content

            if result:
                cache[prompt] = result
                return result
            else:
                logger.warning(f"No result returned for prompt: {prompt}")
                return "No result returned from API."
        except Exception as e:
            logger.error(f"Error during predict call: {e}")
            # Try Groq as emergency fallback
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=MODEL_LLM,
                    max_tokens=256
                )
                return response.choices[0].message.content
            except:
                return "An error occurred while fetching the result."

    def llama(self, user_input):
        """Generate a conversational response using Gemini (primary) or Groq (fallback)."""
        if user_input in cache and cache[user_input] is not None:
            return cache[user_input]
        
        try:
            if gemini_model:
                # Build conversation context for Gemini
                context = "Você é o JARVIS, um assistente de IA inspirado no Iron Man. Responda em português de forma concisa e útil.\n\n"
                response = gemini_model.generate_content(context + user_input)
                result = response.text.strip()
            else:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=messages_normal + [{"role": "user", "content": user_input}],
                    model=MODEL_LLM,
                )
                result = chat_completion.choices[0].message.content
            
            messages_normal.append({"role": "assistant", "content": result})
            cache[user_input] = result
            store_conversations(user_input, result)
            return result if result else "No result returned from API."
        except Exception as e:
            logger.error(f"Error in llama: {e}")
            return "An error occurred while fetching the result."

    def optimize_method(self, prompt):
        """Optimize method for better performance."""
        try:
            result = client.predict(
                prompt=prompt,
                temperature=0.7,
                max_new_tokens=200,
                top_p=0.85,
                repetition_penalty=1.1,
                api_name="/optimize"
            ).replace("</s>", "")
            return result if result else "No result returned from API."
        except Exception as e:
            logger.error(f"Error during optimize call: {e}")
            return "An error occurred while optimizing the result."

    def new_feature_method(self, prompt):
        """New feature method to enhance functionality."""
        try:
            result = client.predict(
                prompt=prompt,
                temperature=0.8,
                max_new_tokens=300,
                top_p=0.9,
                repetition_penalty=1.2,
                api_name="/new_feature"
            ).replace("</s>", "")
            return result if result else "No result returned from API."
        except Exception as e:
            logger.error(f"Error during new feature call: {e}")
            return "An error occurred while fetching the new feature result."

class VectorDB:
    def __init__(self):
        self.vector_db = self._initialize_vector_db()

    def _initialize_vector_db(self):
        """Initialize the vector database, deleting existing collection if necessary."""
        try:
            chromadb_client.delete_collection(name=VECTOR_DB_NAME)
        except ValueError:
            pass
        return chromadb_client.create_collection(name=VECTOR_DB_NAME)

    def safe_create_vector_db(self, messages):
        """Create and store embeddings in the vector database."""
        for message in messages:
            prompt = message['content']
            response = "Sample response based on message content"  # Placeholder response

            serialized_convo = f"prompt: {prompt} response: {response}"
            try:
                embedding_response = ollama.embeddings(model=MODEL_EMBED, prompt=serialized_convo)
                if 'embedding' not in embedding_response or not embedding_response['embedding']:
                    logger.error(f"Empty embedding response for prompt: {prompt}")
                    continue
                embedding = embedding_response['embedding']

                if self.vector_db.get(str(message.get('id', len(messages)))) is not None:
                    logger.warning(f"Embedding ID {message.get('id', len(messages))} already exists. Skipping.")
                    continue

                self.vector_db.add(
                    ids=[str(message.get('id', len(messages)))],
                    embeddings=[embedding],
                    documents=[serialized_convo]
                )
            except Exception as e:
                logger.error(f"Error creating vector DB entry for message: {e}")

    def retrieve_embeddings(self, prompt):
        """Retrieve embeddings from the vector database based on the prompt."""
        try:
            embedding_response = ollama.embeddings(model=MODEL_EMBED, prompt=prompt)
            if 'embedding' not in embedding_response or not embedding_response['embedding']:
                logger.error(f"Empty embedding response for prompt: {prompt}")
                return "No embedding found."
            prompt_embedding = embedding_response['embedding']
            results = self.vector_db.query(query_embeddings=[prompt_embedding], n_results=1)
            if 'documents' in results and results['documents']:
                return results['documents'][0][0]
            else:
                return "No context found."
        except Exception as e:
            logger.error(f"Error retrieving embeddings: {e}")
            return "An error occurred while retrieving context."

def main(prompt_user):
    """Main function to interact with the AI Assistant."""
    ai_client = AIClient()
    vector_db = VectorDB()

    # Initialize vector database with existing conversations
    conversations = fetch_conversations()
    vector_db.safe_create_vector_db(conversations)
    print("Conversations fetched and vector database initialized.")

    print("AI Assistant is running. Type your prompt and press Enter to interact. Press Ctrl+C to exit.")

    try:
        prompt = prompt_user
        if not prompt.strip():
            print("Prompt cannot be empty. Please try again.")
        
        # Retrieve context from vector DB
        context = vector_db.retrieve_embeddings(prompt=prompt)
        if context == "No context found.":
            print(context)
        
        # Format the prompt for the AI model
        formatted_prompt = f"USER PROMPT: {prompt}\nCONTEXT FROM EMBEDDINGS: {context}"
        response = ai_client.llama(formatted_prompt)
        
        print("AI Response:", response)
    
    except KeyboardInterrupt:
        print("\nExiting...")
        exit()

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print("An error occurred. Please check the logs for details.")

if __name__ == "__main__":
    main()
