# Laptop Sales Agent

## Overview

This agent analyzes customer requirements in natural language and recommends the top 3 most suitable laptops from a database. It provides detailed reasoning for each recommendation based on usage profiles, technical specifications, and customer preferences.

## Features

- **Natural Language Processing**: Understands customer needs expressed conversationally
- **Smart Classification**: Automatically detects usage profiles (gaming, student, workstation, basic)
- **Intelligent Filtering**: Applies hard filters (brand, price, specs) when specified
- **Profile-Based Scoring**: Uses weighted scoring system tailored to four usage profiles
- **Reasoning Generation**: Provides clear explanations for each recommendation
- **Memory Persistence**: Maintains conversation context across interactions


## Example Query

- "I am going to uni this year and I need a laptop for taking notes and doing assignments. Money is most important factor for me. I need best price to performance ratio. My budget is 800 euros, i can go a bit higher like 100 extra euro max"

> You can see the result in [TEST 4: Very Specific Student Needs](https://github.com/waellejmi/laptop-sales-agent/blob/main/results/more_results.md) 


## Usage Profiles

The agent supports four distinct profiles with different component priorities:

- **Gaming**: GPU-focused (45% GPU, 30% CPU)
- **Student**: Budget-conscious with balanced performance (40% CPU, 20% price)
- **Basic/Office**: General use, integrated GPU sufficient (35% CPU, 25% RAM)
- **Workstation**: CPU and RAM intensive (55% CPU, 20% RAM)


## Installation

1. Clone the repository
2. Install dependencies:
```bash
uv sync
```

3. Create a `.env` file in the project root:
```env
GROQ_KEY=groq_api_key_here
HF_TOKEN=huggingface_token_here  # Optional
```


## Usage

### Interactive CLI

Run the interactive command-line interface:

```bash
python cli.py
```

### Programmatic Testing

Run predefined test scenarios:

```bash
python tests.py
```

## Project Structure

```
.
├── agent.py              # Main agent implementation (LangGraph workflow)
├── filter.py             # Laptop filtering logic
├── scoring.py            # Scoring system and weight definitions
├── cli.py                # Interactive CLI interface
├── tests.py               # Test suite
├── data/
│   └── laptops_enhanced.csv  # Preprocessed laptop database
├── .env                  # API keys (create this file)
└── pyproject.toml     # Python dependencies
```

## How It Works

1. **User Input**: Customer describes their needs in natural language
2. **Classification**: LLM extracts usage profile, emphasis, and filters
3. **Filtering**: Applies hard filters if specified (brand, price, specs)
4. **Scoring**: Calculates weighted scores based on detected profile
5. **Ranking**: Returns top 3 laptops sorted by score
6. **Explanation**: LLM generates personalized reasoning for recommendations

## Dataset

The agent uses a preprocessed laptop database with normalized scores for:
- CPU performance tiers
- GPU performance tiers
- RAM capacity
- Price (inverted normalization)
- SSD presence

Original kaggle dataset source: [Laptops Dataset](https://www.kaggle.com/datasets/sushmita36/laptops-dataset)

My modified version: [Laptops Specificaitons Dataset](https://www.kaggle.com/datasets/waellejmi/laptops-specificaitons-enhanced/data).

## Error Handling

The agent gracefully handles:
- No matching laptops (suggests adjusting criteria)
- Invalid filters or specifications
- API failures (fallback to TinyLlama)
- Empty or malformed inputs


### Technical Stack

- **LangGraph**: Orchestrates the agent workflow
- **Groq API**: Qwen3-32B model for LLM operations
- **HuggingFace**: TinyLlama fallback model
- **Pandas**: Data processing and filtering
- **Pydantic**: Structured output validation
