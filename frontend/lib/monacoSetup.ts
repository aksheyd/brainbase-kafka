import { Monaco } from "@monaco-editor/react";

/**
 * Sets up the Monaco editor with custom language support for 'based'.
 * This includes defining syntax highlighting rules (tokenizer) and a custom theme.
 * It ensures that the setup only runs once.
 * @param monaco - The Monaco editor instance.
 */
export function setupMonaco(monaco: Monaco) {
  // Check if the 'based' language is already registered
  if (!monaco.languages.getLanguages().some((lang: any) => lang.id === 'based')) {
    
    // Register the 'based' language
    monaco.languages.register({ id: 'based' });

    // Define the Monarch tokenizer for 'based' syntax highlighting
    monaco.languages.setMonarchTokensProvider('based', {
      tokenizer: {
        root: [
          // Control flow keywords
          [/loop:|until:|if |else:|elif /, 'control'],
          // Boolean literals
          [/\b(True|False)\b/, 'boolean'],
          // Logical operators
          [/\b(and|or|not)\b/, 'keyword'],
          // Other keywords
          [/\b(await|return|break|continue)\b/, 'keyword'],
          // Function expressions (specific to 'based' language)
          [/\b(talk|say|ask|api\.get_req|api\.post_req)\b/, 'fexpr'],
          // String literals (double quotes)
          [/".*?"/, 'string'],
          // String literals (single quotes)
          [/'.*?'/, 'string'],
          // Single-line comments (//)
          [/\/\/.*$/, 'comment'],
          // Single-line comments (#)
          [/#.*$/, 'comment'],
          // Numbers (integers and floats)
          [/\b\d+(\.\d+)?\b/, 'number'],
          // Delimiters
          [/[\[\](){},.:;=]/, 'delimiter'],
        ],
      }
    });
    
    // Define a custom theme named 'based-theme' optimized for readability
    monaco.editor.defineTheme('based-theme', {
      base: 'vs-dark', // Inherit from the default dark theme
      inherit: true, // Inherit rules not explicitly defined
      rules: [
        // Custom token styling rules
        { token: 'control', foreground: '569CD6', fontStyle: 'bold' }, // e.g., loop:, if
        { token: 'boolean', foreground: '569CD6' }, // e.g., True, False
        { token: 'fexpr', foreground: '4EC9B0' }, // e.g., talk, say
        { token: 'string', foreground: 'CE9178' }, // e.g., "hello"
        { token: 'comment', foreground: '6A9955', fontStyle: 'italic' }, // e.g., // comment
        { token: 'number', foreground: 'B5CEA8' }, // e.g., 123, 4.5
        // 'delimiter' token uses default foreground color
      ],
      colors: {
        // Editor-wide color overrides
        'editor.background': '#000000', // Pure black background
        'editor.foreground': '#D4D4D4', // Default text color
        'editor.lineHighlightBackground': '#2A2D2E', // Background color of the current line
        'editorCursor.foreground': '#AEAFAD', // Cursor color
        'editor.selectionBackground': '#264F78', // Text selection background color
        'editorIndentGuide.background': '#404040', // Indentation guide line color
      },
    });
  }
}