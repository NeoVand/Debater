import gradio as gr
import requests
import random
import json
from typing import List, Dict, Any, Optional, Tuple

# Default Ollama URL
DEFAULT_OLLAMA_URL = 'http://localhost:11434'

def check_ollama_connection(ollama_url: str) -> bool:
    """
    Checks if the Ollama server is reachable by sending a GET request to the /api/tags endpoint.
    Returns True if the server is reachable, False otherwise.
    """
    try:
        response = requests.get(f'{ollama_url}/api/tags', timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Error connecting to Ollama server: {e}")
        return False

def get_ollama_models(ollama_url: str) -> List[str]:
    """
    Retrieves a list of available models from the Ollama server.
    Returns a list of model names.
    """
    try:
        response = requests.get(f'{ollama_url}/api/tags', timeout=5)
        response.raise_for_status()
        models = [model['name'] for model in response.json()['models']]
        return models
    except requests.RequestException as e:
        print(f"Error fetching models from Ollama server: {e}")
        return []

def generate_output(ollama_url: str, model: str, prompt: str, options: Dict[str, Any]) -> Optional[requests.Response]:
    """
    Generates a response from the Ollama API based on the given prompt and options.
    Returns a requests.Response object if successful, None otherwise.
    """
    try:
        data = {
            'model': model,
            'prompt': prompt,
            'options': options
        }
        response = requests.post(f'{ollama_url}/api/generate',
                                 json=data,
                                 stream=True,
                                 timeout=300)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return None

def main():
    # Create the Gradio Blocks app
    with gr.Blocks() as demo:
        # Fetch initial models from Ollama server
        initial_models: List[str] = get_ollama_models(DEFAULT_OLLAMA_URL)

        # Top bar with topic input, stage rules, control buttons, and debate state
        # First row: Topic, Stage Rules, and Status
        with gr.Row():
            topic = gr.Textbox(
                label="🌍 Topic of Debate",
                placeholder="Enter the topic of the debate",
                value="Climate change",  # Pre-filled with the topic
                scale=1
            )
            stage_rules = gr.Textbox(
                label="📏 Stage Rules",
                placeholder="Enter the stage rules",
                value="Stay on topic and keep your responses short.",
                scale=2
            )
            # Ollama URL input
            ollama_url = gr.Textbox(
                label="🌐 Ollama Server URL",
                value=DEFAULT_OLLAMA_URL,
                interactive=True,
                scale=1
            )
            status = gr.Textbox(
                label="🏁 Debate Status",
                interactive=False,
                scale=1
            )

        # Second row: Control buttons
        with gr.Row():
            start_button = gr.Button("▶️ Start", scale=1)
            stop_button = gr.Button("⏹️ Stop", interactive=False, scale=1)  # Initially disabled
            reset_button = gr.Button("🔄 Reset", scale=1)

        # Main content area
        with gr.Row():
            # Left sidebar for Agent 1 configuration
            with gr.Column(scale=1):
                gr.Markdown("### 🤖 Agent 1 Configuration")
                agent1_name = gr.Textbox(
                    label="👤 Agent Name",
                    value="Climate Scientist"
                )
                agent1_system_prompt = gr.TextArea(
                    label="💬 System Prompt",
                    lines=5,
                    placeholder="Define the role or ideas of Agent 1",
                    value="You are a knowledgeable climate scientist advocating for immediate action to combat climate change."
                )
                agent1_model = gr.Dropdown(
                    label="🧠 Ollama Model",
                    choices=initial_models,
                    value=initial_models[0] if initial_models else "",
                    interactive=True
                )
                agent1_temperature = gr.Slider(
                    label="🌡️ Temperature",
                    minimum=0.0,
                    maximum=2.0,
                    value=1.0
                )
                agent1_top_k = gr.Slider(
                    label="🔝 Top K",
                    minimum=1,
                    maximum=200,
                    value=40
                )
                agent1_memory_size = gr.Slider(
                    label="🧠 Memory Size (characters)",
                    minimum=100,
                    maximum=10000,
                    value=2000
                )

            # Chat area (extended to the bottom)
            with gr.Column(scale=2):
                chat = gr.Chatbot(
                    label="🗨️ Debate Chat",
                    type='messages',
                    height=600  # Adjust this value to extend the chat area
                )

            # Right sidebar for Agent 2 configuration
            with gr.Column(scale=1):
                gr.Markdown("### 🤖 Agent 2 Configuration")
                agent2_name = gr.Textbox(
                    label="👤 Agent Name",
                    value="Conservative Farmer"
                )
                agent2_system_prompt = gr.TextArea(
                    label="💬 System Prompt",
                    lines=5,
                    placeholder="Define the role or ideas of Agent 2",
                    value="You are a conservative farmer skeptical about the impact of human activities on climate change."
                )
                agent2_model = gr.Dropdown(
                    label="🧠 Ollama Model",
                    choices=initial_models,
                    value=initial_models[0] if initial_models else "",
                    interactive=True
                )
                agent2_temperature = gr.Slider(
                    label="🌡️ Temperature",
                    minimum=0.0,
                    maximum=2.0,
                    value=1.0
                )
                agent2_top_k = gr.Slider(
                    label="🔝 Top K",
                    minimum=1,
                    maximum=200,
                    value=40
                )
                agent2_memory_size = gr.Slider(
                    label="🧠 Memory Size (characters)",
                    minimum=100,
                    maximum=10000,
                    value=2000
                )

        # State variable to control debate running status and store conversation
        debate_state = gr.State({'running': False, 'conversation': [], 'chat_history': [], 'message_count': 0, 'current_agent_index': None})

        def update_models(ollama_url: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            """
            Updates the model dropdowns with models from the Ollama server.
            Returns updates for both agent1_model and agent2_model dropdowns.
            """
            models = get_ollama_models(ollama_url)
            if models:
                first_model = models[0]
            else:
                first_model = ""
            return (
                gr.Dropdown.update(choices=models, value=first_model),
                gr.Dropdown.update(choices=models, value=first_model)
            )

        # Update models when Ollama URL changes
        ollama_url.change(
            update_models,
            inputs=[ollama_url],
            outputs=[agent1_model, agent2_model]
        )

        def start_debate(
            topic_text: str,
            stage_rules_text: str,
            agent1_name_text: str, agent1_system_prompt_text: str, agent1_model_name: str, agent1_temperature_value: float, agent1_top_k_value: int, agent1_memory_size_value: int,
            agent2_name_text: str, agent2_system_prompt_text: str, agent2_model_name: str, agent2_temperature_value: float, agent2_top_k_value: int, agent2_memory_size_value: int,
            ollama_url_input: str,
            debate_state: Dict[str, Any]
        ) -> Any:
            """
            Runs the debate between the two agents.
            """
            if debate_state['running']:
                # Debate is already running
                yield gr.update(), gr.update(), gr.update(interactive=False), gr.update(interactive=True)
                return

            if not check_ollama_connection(ollama_url_input):
                yield debate_state['chat_history'], "Cannot connect to Ollama server. Please check the URL and ensure the server is running.", gr.update(interactive=True), gr.update(interactive=False)
                return

            # Initialize agents with their configurations
            agents = [
                {
                    'name': agent1_name_text.strip() or "Agent 1",
                    'system_prompt': agent1_system_prompt_text.strip(),
                    'model': agent1_model_name,
                    'temperature': agent1_temperature_value,
                    'top_k': int(agent1_top_k_value),
                    'memory_size': int(agent1_memory_size_value),
                    'memory': ''
                },
                {
                    'name': agent2_name_text.strip() or "Agent 2",
                    'system_prompt': agent2_system_prompt_text.strip(),
                    'model': agent2_model_name,
                    'temperature': agent2_temperature_value,
                    'top_k': int(agent2_top_k_value),
                    'memory_size': int(agent2_memory_size_value),
                    'memory': ''
                }
            ]

            # Get conversation history and control variables from debate_state
            conversation: List[Dict[str, Any]] = debate_state['conversation']
            chat_history: List[Dict[str, str]] = debate_state['chat_history']
            message_count: int = debate_state.get('message_count', 0)
            current_agent_index: Optional[int] = debate_state.get('current_agent_index')

            if current_agent_index is None:
                # If starting for the first time, pick a random agent
                current_agent_index = random.randint(0, 1)
                debate_state['current_agent_index'] = current_agent_index

            status_text: str = "🚀 Debate started."
            debate_state['running'] = True

            # Disable the start button and enable the stop button
            yield chat_history, status_text, gr.update(interactive=False), gr.update(interactive=True)

            while message_count < 1000 and debate_state['running']:
                agent = agents[current_agent_index]

                # Prepare the memory from the conversation, limited by memory_size
                memory_text = ''
                memory_length = 0
                for msg in reversed(conversation):
                    msg_text = f"{msg['name']}: {msg['content']}\n"
                    memory_length += len(msg_text)
                    if memory_length > agent['memory_size']:
                        break
                    memory_text = msg_text + memory_text

                # Prepare the prompt for the agent
                prompt = (
                    f"{agent['system_prompt']}\n\n"
                    f"{stage_rules_text.strip()}\n\n"
                    f"Topic: {topic_text.strip()}\n\n"
                    f"{memory_text}"
                    f"{agent['name']}:"
                )

                # Options for the model generation
                options = {
                    'temperature': agent['temperature'],
                    'top_k': agent['top_k'],
                    'stop': [f"{agents[1 - current_agent_index]['name']}:"]  # Stop when the other agent's name appears
                }

                # Generate response from the model
                response = generate_output(ollama_url_input, agent['model'], prompt, options)

                if response:
                    full_response = ''
                    role = 'user' if current_agent_index == 0 else 'assistant'
                    # Add a new message with empty content
                    chat_history.append({'role': role, 'content': f"{agent['name']}: "})
                    conversation.append({
                        'name': agent['name'],
                        'content': ''
                    })
                    message_count += 1

                    # Stream the response and update the chat in real-time
                    for line in response.iter_lines():
                        if not debate_state['running']:
                            break
                        if line:
                            json_response = json.loads(line.decode('utf-8'))
                            if 'response' in json_response:
                                partial_response = json_response['response']
                                full_response += partial_response

                                # Update the last message in chat history
                                chat_history[-1]['content'] = f"{agent['name']}: {full_response}"
                                conversation[-1]['content'] = full_response

                                # Update status
                                status_text = f"{agent['name']} is typing..."

                                # Yield the updated conversation and status
                                yield chat_history, status_text, gr.update(interactive=False), gr.update(interactive=True)
                    full_response = full_response.strip()
                else:
                    full_response = "Error generating response."
                    # Update the last message in chat history
                    chat_history[-1]['content'] = f"{agent['name']}: {full_response}"
                    conversation[-1]['content'] = full_response

                    # Update status
                    status_text = f"{agent['name']} encountered an error."

                    # Yield the updated conversation and status
                    yield chat_history, status_text, gr.update(interactive=False), gr.update(interactive=True)

                # Check if debate has been stopped
                if not debate_state['running']:
                    status_text = "🛑 Debate stopped."
                    debate_state['current_agent_index'] = current_agent_index
                    debate_state['message_count'] = message_count
                    yield chat_history, status_text, gr.update(interactive=True), gr.update(interactive=False)
                    break

                # Update status after agent finishes typing
                status_text = f"{agent['name']} finished responding."

                # Yield the final update for this turn
                yield chat_history, status_text, gr.update(interactive=False), gr.update(interactive=True)

                # Switch to the other agent
                current_agent_index = 1 - current_agent_index

                # Update debate_state with the new current_agent_index and message_count
                debate_state['current_agent_index'] = current_agent_index
                debate_state['message_count'] = message_count

            if message_count >= 1000:
                status_text = "Debate ended after reaching message limit."
                debate_state['running'] = False
                yield chat_history, status_text, gr.update(interactive=True), gr.update(interactive=False)

            # Re-enable the start button and disable the stop button
            debate_state['running'] = False
            debate_state['current_agent_index'] = current_agent_index
            debate_state['message_count'] = message_count
            yield chat_history, status_text, gr.update(interactive=True), gr.update(interactive=False)

        def stop_debate(debate_state: Dict[str, Any]) -> Tuple[Any, str, Dict[str, Any], Dict[str, Any]]:
            """
            Stops the ongoing debate by setting the running state to False.
            """
            debate_state['running'] = False
            return gr.update(), "🛑 Debate stopped.", gr.update(interactive=True), gr.update(interactive=False)

        def reset_debate(debate_state: Dict[str, Any]) -> Tuple[List[Any], str, Dict[str, Any], Dict[str, Any]]:
            """
            Resets the debate by clearing the chat history and resetting the running state.
            """
            debate_state['running'] = False
            debate_state['conversation'] = []
            debate_state['chat_history'] = []
            debate_state['message_count'] = 0
            debate_state['current_agent_index'] = None
            return [], "🔄 Debate reset.", gr.update(interactive=True), gr.update(interactive=False)

        # Button event handlers
        start_button.click(
            start_debate,
            inputs=[
                topic,
                stage_rules,
                agent1_name, agent1_system_prompt, agent1_model, agent1_temperature, agent1_top_k, agent1_memory_size,
                agent2_name, agent2_system_prompt, agent2_model, agent2_temperature, agent2_top_k, agent2_memory_size,
                ollama_url,
                debate_state
            ],
            outputs=[
                chat, status, start_button, stop_button
            ],
            queue=True
        )

        stop_button.click(
            stop_debate,
            inputs=[debate_state],
            outputs=[chat, status, start_button, stop_button]
        )

        reset_button.click(
            reset_debate,
            inputs=[debate_state],
            outputs=[chat, status, start_button, stop_button]
        )

    if __name__ == "__main__":
        demo.queue().launch()

main()
