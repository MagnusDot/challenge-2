import sys
import io

class FilteredOutput:
    def __init__(self, original_stream, filter_patterns):
        self.original_stream = original_stream
        self.filter_patterns = filter_patterns
        self.buffer = ""
    
    def write(self, text):
        if not text:
            return
        
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            should_filter = False
            line_stripped = line.strip()
            
            if not line_stripped:
                filtered_lines.append(line)
                continue
            
            for pattern in self.filter_patterns:
                if pattern in line_stripped:
                    should_filter = True
                    break
            
            if not should_filter:
                filtered_lines.append(line)
        
        if filtered_lines:
            filtered_text = '\n'.join(filtered_lines)
            self.original_stream.write(filtered_text)
    
    def flush(self):
        self.original_stream.flush()
    
    def __getattr__(self, name):
        return getattr(self.original_stream, name)


def setup_output_filter():
    filter_patterns = [
        "Provider List: https://docs.litellm.ai/docs/providers",
        "Provider List",
        "LiteLLM.Info:",
        "LiteLLM.Info",
        "Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new",
        "Give Feedback / Get Help:",
        "If you need to debug this error, use `litellm._turn_on_debug()'",
        "litellm._turn_on_debug",
    ]
    
    sys.stdout = FilteredOutput(sys.stdout, filter_patterns)
    sys.stderr = FilteredOutput(sys.stderr, filter_patterns)
