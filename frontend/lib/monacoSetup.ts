export function setupMonaco(monaco: any) {
  // Register the Based language if not already registered
  if (!monaco.languages.getLanguages().some((lang: any) => lang.id === 'based')) {
    monaco.languages.register({ id: 'based' });
    
    monaco.languages.setMonarchTokensProvider('based', {
      // Basic tokenizers for the BASED language
      tokenizer: {
        root: [
          [/loop:|until:|if |else:|elif /, 'control'],
          [/\b(True|False)\b/, 'boolean'],
          [/\b(and|or|not)\b/, 'keyword'],
          [/\b(await|return|break|continue)\b/, 'keyword'],
          [/\b(talk|say|ask|api\.get_req|api\.post_req)\b/, 'fexpr'],
          [/\".*?\"/, 'string'],
          [/'.*?'/, 'string'],
          [/\/\/.*$/, 'comment'],
          [/#.*$/, 'comment'],
          [/\b\d+(\.\d+)?\b/, 'number'],
          [/[\[\](){},.:;=]/, 'delimiter'],
        ],
      }
    });
    
    // Define a custom theme optimized for readability
    monaco.editor.defineTheme('based-theme', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'control', foreground: '569CD6', fontStyle: 'bold' },
        { token: 'boolean', foreground: '569CD6' },
        { token: 'fexpr', foreground: '4EC9B0' },
        { token: 'string', foreground: 'CE9178' },
        { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
        { token: 'number', foreground: 'B5CEA8' },
      ],
      colors: {
        'editor.background': '#000000',
        'editor.foreground': '#D4D4D4',
        'editor.lineHighlightBackground': '#2A2D2E',
        'editorCursor.foreground': '#AEAFAD',
        'editor.selectionBackground': '#264F78',
        'editorIndentGuide.background': '#404040',
      },
    });
  }
} 