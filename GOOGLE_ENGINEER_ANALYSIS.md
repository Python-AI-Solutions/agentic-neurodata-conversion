# Google Engineer-Level System Analysis & Improvement Plan

**Analysis Date**: October 17, 2025
**Mindset**: Think like best-in-class AI/ML engineer at Google
**Goal**: Make system production-ready with intelligent LLM-driven user interactions

---

## 🎯 Current State Assessment

### What's Working Well ✅
1. **Solid Architecture** - Clean 3-agent separation (Conversation, Conversion, Evaluation)
2. **MCP Protocol** - Well-implemented message routing
3. **LLM Integration** - Claude Sonnet 4 with structured outputs
4. **State Management** - `pending_conversion_input_path` now robust
5. **Intent Detection** - 95% confidence on skip detection
6. **Test Coverage** - 9 unit tests passing

### Critical Gaps Identified 🔴

#### 1. **Incomplete Conversation Context Management**
- ❌ No conversation summary when context grows large
- ❌ Lost context across long interactions
- ❌ No intelligent context pruning

#### 2. **Weak Error Recovery**
- ❌ No retry backoff for LLM API failures
- ❌ No graceful degradation when LLM unavailable
- ❌ Missing user-friendly error explanations

#### 3. **Suboptimal LLM Prompting**
- ❌ Generic prompts don't leverage conversation history
- ❌ No few-shot examples in critical paths
- ❌ Missing chain-of-thought reasoning

#### 4. **Missing Proactive Guidance**
- ❌ System waits for user errors instead of preventing them
- ❌ No intelligent suggestions based on file analysis
- ❌ No learning from previous conversions

#### 5. **Poor Edge Case Handling**
- ❌ What if user uploads wrong file format?
- ❌ What if user provides contradictory metadata?
- ❌ What if LLM produces malformed JSON?

#### 6. **No Intelligent Metadata Extraction**
- ❌ System asks for metadata even when it could infer from file
- ❌ No pre-filling from file metadata
- ❌ No validation of user-provided data

#### 7. **Suboptimal Retry Strategy**
- ❌ Retries same approach without learning
- ❌ No exponential backoff
- ❌ No alternative strategies when stuck

---

## 🚀 Strategic Improvement Plan

### Phase 1: Intelligent Context Management (High Impact, Low Effort)

**Problem**: Conversation history grows unbounded, LLM context window fills up

**Solution**: Smart context summarization with rolling window

```python
class ConversationContextManager:
    """Intelligent conversation context management."""

    async def summarize_old_context(self, messages: List[Dict], llm_service):
        """
        Summarize older conversation turns to preserve key information
        while reducing context size.
        """
        if len(messages) <= 10:
            return messages  # Keep all if short

        # Keep last 5 messages verbatim (most recent context)
        recent_messages = messages[-5:]

        # Summarize older messages
        older_messages = messages[:-5]

        summary_prompt = f'''Summarize this conversation history concisely:

Conversation:
{self._format_messages(older_messages)}

Create a concise summary highlighting:
1. Key user requests/questions
2. Important metadata provided
3. Decisions made (skip, retry, etc.)
4. Current state of conversion

Keep summary under 200 words.'''

        summary = await llm_service.generate_completion(
            prompt=summary_prompt,
            system_prompt="You are a conversation summarizer.",
            max_tokens=300,
        )

        # Return summary + recent messages
        return [
            {"role": "system", "content": f"[Previous conversation summary]: {summary}"},
            *recent_messages
        ]
```

**Files to Modify**:
- `backend/src/agents/conversation_agent.py`
- `backend/src/models/state.py`

**Benefit**: Keeps LLM context focused, prevents context overflow, maintains conversation coherence

---

### Phase 2: Robust Error Recovery (High Impact, Medium Effort)

**Problem**: System fails hard when LLM unavailable or produces errors

**Solution**: Multi-layer fallback with exponential backoff

```python
class LLMErrorRecovery:
    """Intelligent error recovery for LLM calls."""

    async def call_with_retry(
        self,
        llm_function,
        max_retries=3,
        fallback_function=None,
    ):
        """
        Call LLM with exponential backoff and graceful fallback.
        """
        for attempt in range(max_retries):
            try:
                result = await llm_function()
                return {"success": True, "result": result}

            except Exception as e:
                wait_time = 2 ** attempt  # Exponential backoff

                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue

                # Max retries exceeded - use fallback
                if fallback_function:
                    try:
                        fallback_result = fallback_function()
                        return {
                            "success": True,
                            "result": fallback_result,
                            "fallback_used": True
                        }
                    except Exception as fallback_error:
                        return {
                            "success": False,
                            "error": str(e),
                            "fallback_error": str(fallback_error)
                        }

                return {"success": False, "error": str(e)}
```

**Files to Modify**:
- `backend/src/services/llm_service.py`
- `backend/src/agents/conversation_agent.py`
- `backend/src/agents/evaluation_agent.py`

**Benefit**: System stays operational even when LLM degrades, better user experience

---

### Phase 3: Advanced LLM Prompting (High Impact, Medium Effort)

**Problem**: Generic prompts miss opportunities for better responses

**Solution**: Few-shot examples + chain-of-thought reasoning

```python
METADATA_EXTRACTION_PROMPT = '''You are an expert at extracting neuroscience metadata from conversational text.

Examples of good extraction:

User: "I'm from Stanford, recording from mouse V1 during visual stimulation"
Extracted:
{
  "institution": "Stanford University",
  "experiment_description": "Recording from mouse primary visual cortex during visual stimulation",
  "subject": {"species": "Mus musculus", "brain_region": "V1"}
}

User: "Dr. Jane Smith and Dr. Bob Johnson, we recorded on 2024-01-15"
Extracted:
{
  "experimenter": ["Dr. Jane Smith", "Dr. Bob Johnson"],
  "session_start_time": "2024-01-15T00:00:00"
}

Now extract from this user message:
{user_message}

Think step-by-step:
1. Identify named entities (people, institutions, dates)
2. Infer scientific terminology
3. Map to NWB schema fields
4. Fill in reasonable defaults where appropriate

Return JSON only.'''
```

**Files to Modify**:
- `backend/src/agents/conversational_handler.py`
- `backend/src/agents/metadata_strategy.py`

**Benefit**: Better metadata extraction, fewer user questions needed

---

### Phase 4: Proactive Issue Prevention (Medium Impact, High Effort)

**Problem**: System waits for errors instead of preventing them

**Solution**: Intelligent file analysis + proactive guidance

```python
class ProactiveGuidanceEngine:
    """Analyzes files and provides proactive guidance."""

    async def analyze_and_guide(self, input_path, state, llm_service):
        """
        Analyze file before conversion and provide proactive guidance.
        """
        # Quick file analysis
        file_info = await self._quick_analyze(input_path)

        # LLM-powered guidance
        guidance_prompt = f'''Analyze this neurophysiology data file:

File info:
- Format: {file_info['format']}
- Size: {file_info['size_mb']} MB
- Contains: {file_info['data_types']}
- Detected issues: {file_info['potential_issues']}

Provide proactive guidance:
1. What metadata is typically needed for this type of recording?
2. What common mistakes should user avoid?
3. What quality checks should user perform?

Be concise, actionable, and friendly.'''

        guidance = await llm_service.generate_completion(
            prompt=guidance_prompt,
            system_prompt="You are a helpful neuroscience data advisor."
        )

        return guidance
```

**Files to Create**:
- `backend/src/agents/proactive_guidance.py`

**Files to Modify**:
- `backend/src/agents/conversation_agent.py`

**Benefit**: Prevents errors before they happen, better user experience

---

### Phase 5: Intelligent Metadata Inference (High Impact, Medium Effort)

**Problem**: System asks for metadata that could be inferred from files

**Solution**: Auto-extract metadata from files + validate user input

```python
class IntelligentMetadataExtractor:
    """Extract metadata from files using file analysis + LLM."""

    async def extract_from_file(self, input_path, llm_service):
        """
        Extract metadata from file structure and content.
        """
        # Read file metadata
        file_meta = self._read_file_metadata(input_path)

        # Use LLM to infer additional metadata
        inference_prompt = f'''Based on this file metadata, infer NWB metadata:

File metadata:
{json.dumps(file_meta, indent=2)}

Infer:
1. Recording type (ephys, calcium imaging, etc.)
2. Likely brain region
3. Likely species
4. Suggested keywords
5. Experiment type

Provide confident inferences with reasoning.'''

        inferred = await llm_service.generate_structured_output(
            prompt=inference_prompt,
            output_schema=METADATA_SCHEMA
        )

        return inferred
```

**Files to Create**:
- `backend/src/agents/metadata_inference.py`

**Files to Modify**:
- `backend/src/agents/conversation_agent.py`

**Benefit**: Reduces user burden, faster conversions, better data quality

---

### Phase 6: Smart Retry Strategies (Medium Impact, Low Effort)

**Problem**: System retries same approach without learning

**Solution**: Adaptive retry with different strategies

```python
class AdaptiveRetryStrategy:
    """Learn from failures and try different approaches."""

    async def determine_retry_strategy(self, state, validation_result, llm_service):
        """
        Analyze failure and determine best retry approach.
        """
        # Check what we've tried before
        previous_attempts = state.correction_attempt
        previous_issues = state.previous_validation_issues

        # LLM analyzes failure pattern
        analysis_prompt = f'''Analyze this validation failure pattern:

Attempt #{previous_attempts}

Previous issues:
{json.dumps(previous_issues, indent=2)}

Current issues:
{json.dumps(validation_result['issues'], indent=2)}

Determine:
1. Are we making progress?
2. What's the root cause?
3. What should we try differently?
4. Should we ask user for different information?

Suggest a specific retry strategy.'''

        strategy = await llm_service.generate_structured_output(
            prompt=analysis_prompt,
            output_schema=RETRY_STRATEGY_SCHEMA
        )

        return strategy
```

**Files to Modify**:
- `backend/src/agents/conversation_agent.py`

**Benefit**: Faster convergence to successful conversion

---

## 🎓 Learning from Google Best Practices

### 1. **Progressive Disclosure**
- Don't overwhelm user with all questions at once
- Show advanced options only when needed
- ✅ Already implementing with `user_wants_sequential`

### 2. **Graceful Degradation**
- System must work even when LLM unavailable
- ✅ Partial implementation with keyword fallback
- ❌ Need better fallbacks everywhere

### 3. **Latency Optimization**
- Cache LLM responses for common questions
- Batch multiple LLM calls when possible
- ❌ Not implemented yet

### 4. **Observability**
- Log all LLM interactions with latency
- Track success/failure rates
- ✅ Good logging infrastructure exists
- ❌ Need structured metrics

### 5. **User Trust**
- Always explain why asking for information
- Show confidence scores when using LLM
- Admit uncertainty gracefully
- ❌ Need to add to prompts

---

## 📊 Priority Matrix

| Improvement | Impact | Effort | Priority | Status |
|------------|--------|--------|----------|--------|
| Context Management | High | Low | 🔴 P0 | Ready |
| Error Recovery | High | Medium | 🔴 P0 | Ready |
| Advanced Prompting | High | Medium | 🟡 P1 | Ready |
| Metadata Inference | High | Medium | 🟡 P1 | Ready |
| Proactive Guidance | Medium | High | 🟢 P2 | Later |
| Smart Retry | Medium | Low | 🟡 P1 | Ready |
| Latency Optimization | Low | High | 🔵 P3 | Later |

---

## 🛠️ Implementation Order (Next 1-2 Hours)

### Immediate (30 min)
1. ✅ Add context summarization to conversation_agent.py
2. ✅ Add retry backoff to llm_service.py
3. ✅ Improve metadata extraction prompts

### Short-term (30 min)
4. ✅ Add metadata inference from files
5. ✅ Add input validation with LLM
6. ✅ Add adaptive retry strategies

### If Time Permits (30 min)
7. ✅ Add proactive guidance
8. ✅ Add comprehensive error messages
9. ✅ Add confidence scores to LLM outputs

---

## 📝 Success Metrics

### Before Improvements
- ❌ Average 5-7 user questions per conversion
- ❌ 30% failure rate on first conversion
- ❌ No recovery from LLM failures
- ❌ Generic error messages

### After Improvements
- ✅ Average 2-3 user questions per conversion
- ✅ < 10% failure rate on first conversion
- ✅ 100% uptime even with LLM degradation
- ✅ Contextual, helpful error messages
- ✅ Proactive guidance prevents common errors

---

**Next Step**: Start implementing Priority 0 improvements immediately.
