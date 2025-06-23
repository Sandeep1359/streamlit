import streamlit as st
import json
import requests
import re
import uuid
import time
import base64

# -------------------- CONFIGURATION --------------------
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]



# Repository configuration - you can change these
GITHUB_USERNAME = "Sandeep1359"  # Replace with your GitHub username
REPO_NAME = "notebook-analyzer"  # Repository name for storing temporary files

# -------------------- NOTEBOOK EXTRACTION --------------------
def extract_notebook_content(notebook_data):
    content_parts = []
    try:
        cells = notebook_data.get('cells') or \
                notebook_data.get('worksheets', [{}])[0].get('cells', [])
        for cell in cells:
            cell_type = cell.get('cell_type', '')
            source = cell.get('source', [])
            source_text = ''.join(source) if isinstance(source, list) else str(source)
            if cell_type == 'markdown':
                content_parts.append(f"[MARKDOWN CELL]\n{source_text}\n")
            elif cell_type == 'code':
                content_parts.append(f"[CODE CELL]\n{source_text}\n")
            elif cell_type == 'raw':
                content_parts.append(f"[RAW CELL]\n{source_text}\n")
    except Exception as e:
        return "Error: Could not extract notebook content"
    return '\n'.join(content_parts)

# -------------------- GITHUB REPOSITORY FUNCTIONS --------------------
def ensure_repository_exists():
    """Create repository if it doesn't exist"""
    if not GITHUB_TOKEN:
        return {'success': False, 'error': 'GitHub token not configured'}
    
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        # Check if repository exists
        response = requests.get(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return {'success': True, 'message': 'Repository already exists'}
        elif response.status_code == 404:
            # Create repository
            repo_data = {
                "name": REPO_NAME,
                "description": "Temporary repository for notebook analysis - auto-managed",
                "private": True,
                "auto_init": True
            }
            
            create_response = requests.post(
                "https://api.github.com/user/repos",
                headers=headers,
                data=json.dumps(repo_data),
                timeout=30
            )
            
            if create_response.status_code == 201:
                return {'success': True, 'message': 'Repository created successfully'}
            else:
                return {'success': False, 'error': f"Failed to create repository: {create_response.status_code}"}
        else:
            return {'success': False, 'error': f"Error checking repository: {response.status_code}"}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_file_in_repo(content, filename):
    """Create a file in the GitHub repository and return the URL"""
    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
        return {'success': False, 'error': 'GitHub token not configured'}
    
    try:
        # Ensure repository exists
        repo_result = ensure_repository_exists()
        if not repo_result['success']:
            return repo_result
        
        unique_id = str(uuid.uuid4())[:8]
        unique_filename = f"temp_{filename}_{unique_id}.txt"
        
        # Encode content to base64
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        file_data = {
            "message": f"Add temporary notebook content: {unique_filename}",
            "content": content_encoded,
            "branch": "main"
        }
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        response = requests.put(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{unique_filename}",
            headers=headers,
            data=json.dumps(file_data),
            timeout=30
        )
        
        if response.status_code == 201:
            file_info = response.json()
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/main/{unique_filename}"
            return {
                'success': True,
                'filename': unique_filename,
                'file_url': file_info['content']['html_url'],
                'raw_url': raw_url,
                'sha': file_info['content']['sha']
            }
        else:
            return {'success': False, 'error': f"GitHub API error: {response.status_code} - {response.text}"}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def delete_file_from_repo(filename, sha):
    """Delete a file from the GitHub repository"""
    if not GITHUB_TOKEN or GITHUB_TOKEN == "your_github_token_here":
        return False
    
    try:
        file_data = {
            "message": f"Delete temporary file: {filename}",
            "sha": sha,
            "branch": "main"
        }
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        response = requests.delete(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{filename}",
            headers=headers,
            data=json.dumps(file_data),
            timeout=30
        )
        
        return response.status_code == 200
        
    except Exception as e:
        st.error(f"Error deleting file: {str(e)}")
        return False

def get_github_username():
    if not GITHUB_TOKEN :
        return None
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(
            "https://api.github.com/user",
            headers=headers,
            timeout=30
        )
        print("DEBUG USER API STATUS:", response.status_code)
        print("DEBUG USER API RESPONSE:", response.text)
        if response.status_code == 200:
            user_info = response.json()
            return user_info['login']
        else:
            return None
    except Exception as e:
        print("DEBUG USER API ERROR:", e)
        return None


# -------------------- ANALYSIS FUNCTIONS --------------------
def create_analysis_prompt_with_url(file_url):
    """Create analysis prompt using GitHub raw file URL"""
    prompt = f"""Fetch and analyze notebook at: {file_url}

Return ONLY JSON format:
{{
  "grade": "A/B/C/D/E",
  "scope_of_improvement": [
    "First specific improvement for code structure/optimization",
    "Second improvement for algorithm/implementation"
  ],
  "knowledge_base": [
    "First technical assessment of methods/algorithms used",
    "Second insight on implementation or conceptual issues"
  ]
}}

Required ML steps: problem analysis, data load, checks, EDA (hist/box), insights, feature/target split, train/test split, no leakage, 2+ models, metrics, comments, hyperparameter tuning.

Grades: A=excellent+complete, B=good+minor issues, C=average+several gaps, D=below average+major issues, E=poor+significant problems

Provide specific, actionable feedback only."""
    
    return prompt

def create_analysis_prompt_direct(notebook_content):
    """Fallback: Create analysis prompt with direct content"""
    # Truncate content if too long to avoid token limits
    max_content_length = 8000
    if len(notebook_content) > max_content_length:
        notebook_content = notebook_content[:max_content_length] + "\n\n[CONTENT TRUNCATED DUE TO LENGTH]"
    
    prompt = f"""
You are an expert Python code reviewer and data science mentor. Analyze the following Jupyter Notebook and provide a detailed JSON analysis, **with each field always filled and at least 2 bullet points in both 'scope_of_improvement' and 'knowledge_base'**.

NOTEBOOK CONTENT:
{notebook_content}

**Strictly reply in the following valid JSON format (do NOT use markdown or explanations):**

{{
    "grade": "A/B/C/D/E",
    "scope_of_improvement": [
      "First clear suggestion for improving code structure, modularity, optimization, or documentation.",
      "Second suggestion, e.g. about better algorithm use, error handling, or code clarity."
    ],
    "knowledge_base": [
      "Assessment of chosen algorithms/methods and their suitability.",
      "Insight on evaluation metrics, implementation flaws, or deeper conceptual issues."
    ]
}}

- Never leave any field blank. Always provide actionable, non-generic, specific feedback.
- If the code is minimal, still suggest at least two improvements and two knowledge points.

GRADING CRITERIA:
A: Excellent, B: Good, C: Average, D: Below average, E: Poor.
"""
    return prompt

def parse_response(ai_content):
    try:
        start_idx = ai_content.find('{')
        end_idx = ai_content.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            return json.loads(ai_content[start_idx:end_idx])
    except Exception:
        pass

    result = {"grade": "n/a", "scope_of_improvement": [], "knowledge_base": []}
    grade_match = re.search(r'grade\s*[:=]\s*["\']?([A-E])', ai_content, re.I)
    if grade_match:
        result["grade"] = grade_match.group(1).upper()

    for field in ['scope_of_improvement', 'knowledge_base']:
        bullet_list = re.findall(rf'{field}\s*[:=]\s*(\[.*?\])', ai_content, re.S | re.I)
        if bullet_list:
            try:
                result[field] = json.loads(bullet_list[0])
            except Exception:
                items = re.split(r'[-*]\s+', bullet_list[0])
                result[field] = [item.strip().strip('",') for item in items if item.strip()]
        else:
            lines = re.findall(rf'{field}\s*[:=]?.*?\n((?:\s*[-*].*\n?)+)', ai_content, re.I)
            if lines:
                result[field] = [line.strip('-* \n') for line in lines[0].split('\n') if line.strip()]
    
    if not result["scope_of_improvement"]:
        result["scope_of_improvement"] = ["Analysis completed but could not parse improvement suggestions."]
    if not result["knowledge_base"]:
        result["knowledge_base"] = ["Analysis completed but could not parse knowledge assessment."]
    
    return result

def analyze_with_openrouter(prompt):
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:8501',
        'X-Title': 'Notebook Evaluator'
    }
    payload = {
        "model": "deepseek/deepseek-r1-0528:free",
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }
    try:
        response = requests.post(
            url=f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )
        if response.status_code != 200:
            return None, f"OpenRouter API error: {response.status_code} - {response.text}"
        res_json = response.json()
        if 'choices' not in res_json or not res_json['choices']:
            return None, f"Unexpected response: {res_json}"
        ai_content = res_json['choices'][0]['message']['content']
        analysis_result = parse_response(ai_content)
        return analysis_result, None
    except Exception as e:
        return None, f"Request failed: {str(e)}"

# -------------------- STREAMLIT APP --------------------
st.set_page_config(page_title="Jupyter Notebook Evaluator (GitHub Repo)", page_icon="📝", layout="centered")
st.title("📝 Jupyter Notebook Evaluator (GitHub Repository)")
st.markdown("Upload a `.ipynb` file to receive an instant, AI-powered evaluation of your notebook's code quality, methodology, and completeness.")

# Auto-detect GitHub username
if GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here":
    detected_username = get_github_username()
    # if detected_username:
    #     GITHUB_USERNAME = detected_username
    #     st.info(f"✅ GitHub Repository integration enabled. Using username: **{GITHUB_USERNAME}**")
    #     st.info(f"📁 Repository: **{GITHUB_USERNAME}/{REPO_NAME}**")
    # else:
    #     st.warning("⚠️ Could not detect GitHub username. Please update GITHUB_USERNAME in the code.")
else:
    st.warning("⚠️ GitHub token not configured. Using direct content method (may hit token limits for large notebooks).")

uploaded_file = st.file_uploader(
    "Upload your Jupyter Notebook (.ipynb only)", type=["ipynb"], accept_multiple_files=False
)

if uploaded_file:
    file_info = None  # Track file for cleanup
    
    try:
        notebook_json = json.load(uploaded_file)
        notebook_content = extract_notebook_content(notebook_json)
        
        if notebook_content.startswith("Error:"):
            st.error("Failed to extract notebook content. Please check your file.")
        else:
            st.info(f"📊 Extracted content length: {len(notebook_content)} characters")
            
            with st.spinner("Analyzing your notebook with AI..."):
                # Try GitHub repository method first if token is configured
                if GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here" and GITHUB_USERNAME != "your-username":
                    st.info("📤 Creating temporary file in GitHub repository...")
                    
                    filename = uploaded_file.name.replace('.ipynb', '') if uploaded_file.name.endswith('.ipynb') else 'notebook'
                    file_result = create_file_in_repo(notebook_content, filename)
                    
                    if file_result['success']:
                        file_info = file_result
                        raw_url = file_result['raw_url']
                        
                        st.success(f"📁 File created: **{file_result['filename']}**")
                        st.info(f"🔗 Raw URL: {raw_url}")
                        st.info("🤖 Sending to AI for analysis...")
                        
                        # Small delay to ensure file is available
                        time.sleep(2)
                        
                        prompt = create_analysis_prompt_with_url(raw_url)
                        analysis, error = analyze_with_openrouter(prompt)
                        
                    else:
                        st.warning(f"Failed to create file in repository: {file_result.get('error', 'Unknown error')}")
                        st.info("📝 Falling back to direct content method...")
                        prompt = create_analysis_prompt_direct(notebook_content)
                        analysis, error = analyze_with_openrouter(prompt)
                else:
                    st.info("📝 Using direct content method...")
                    prompt = create_analysis_prompt_direct(notebook_content)
                    analysis, error = analyze_with_openrouter(prompt)
            
            # Display results
            if error:
                st.error(f"Analysis failed: {error}")
            elif analysis:
                grade = analysis.get('grade', 'N/A')
                grade_colors = {'A': '🟢', 'B': '🔵', 'C': '🟡', 'D': '🟠', 'E': '🔴'}
                grade_emoji = grade_colors.get(grade, '⚪')
                
                st.success(f"**{grade_emoji} Grade: {grade}**")
                
                st.markdown("### 📈 Scope of Improvement")
                if isinstance(analysis.get('scope_of_improvement'), list):
                    for i, point in enumerate(analysis['scope_of_improvement'], 1):
                        st.write(f"{i}. {point}")
                else:
                    st.write(analysis.get('scope_of_improvement', 'No suggestions returned.'))
                
                st.markdown("### 💡 Knowledge Base Assessment")
                if isinstance(analysis.get('knowledge_base'), list):
                    for i, point in enumerate(analysis['knowledge_base'], 1):
                        st.write(f"{i}. {point}")
                else:
                    st.write(analysis.get('knowledge_base', 'No analysis returned.'))
                
                with st.expander("🔍 Raw AI Response"):
                    st.json(analysis)
                    
    except json.JSONDecodeError:
        st.error("Invalid notebook file format. Please upload a valid .ipynb file.")
    except Exception as e:
        st.error(f"Error processing file: {e}")
    
    finally:
        # Clean up: Delete the file after analysis
        if file_info:
            try:
                time.sleep(2)  # Ensure AI has processed the file
                delete_success = delete_file_from_repo(file_info['filename'], file_info['sha'])
                if delete_success:
                    st.success(f"🗑️ Cleaned up temporary file: **{file_info['filename']}**")
                else:
                    st.warning(f"⚠️ Could not clean up file: **{file_info['filename']}** (you may need to delete it manually)")
            except Exception as cleanup_error:
                st.warning(f"Error during cleanup: {cleanup_error}")

st.markdown("---")
# st.caption("🔒 No data is stored permanently. Powered by AI via OpenRouter API.")
# st.caption(f"📁 Temporary files are created in **{GITHUB_USERNAME}/{REPO_NAME}** and automatically deleted after analysis.")

# Configuration instructions
with st.expander("⚙️ Configuration Instructions"):
    st.markdown(f"""
    **GitHub Repository Setup:**
    
    1. **Repository Configuration:**
       - Repository: `{GITHUB_USERNAME}/{REPO_NAME}`
       - The repository will be created automatically if it doesn't exist
       - Files are temporarily stored and then deleted after analysis
    
    2. **GitHub Token Requirements:**
       - Your token needs `repo` scope for private repositories
       - Or `public_repo` scope for public repositories
       - Current token: `{GITHUB_TOKEN[:20]}...`
    
    3. **How it works:**
       - Creates a temporary file in your GitHub repository
       - Generates a raw URL for the AI to access
       - Automatically deletes the file after analysis
       - Repository is created as private by default
    
    4. **Benefits over Gists:**
       - More control over file organization
       - Can use existing repositories
       - Better integration with your GitHub workflow
    
    **Note:** The repository `{REPO_NAME}` will be created automatically in your account if it doesn't exist.
    """)

# Repository status
with st.expander("📁 Repository Status"):
    if st.button("Check Repository Status"):
        if GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here":
            repo_status = ensure_repository_exists()
            if repo_status['success']:
                st.success(f"✅ {repo_status['message']}")
                # st.info(f"🔗 Repository URL: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")
            else:
                st.error(f"❌ {repo_status['error']}")
        else:
            st.warning("GitHub token not configured")
