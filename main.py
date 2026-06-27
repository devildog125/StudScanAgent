
from dotenv import load_dotenv

load_dotenv()

from langchain.chat_models import init_chat_model
from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langsmith import traceable



def main():
    print("Hello from studscanagent!")


if __name__ == "__main__":
    main()
