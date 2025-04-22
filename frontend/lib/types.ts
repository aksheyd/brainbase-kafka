export type DiffState = {
    diff: string | null;
    old_code?: string | null;
    new_code?: string | null;
};

export type ChatMessage = {
    id: string;
    role: 'user' | 'agent' | 'system';
    content: string;
};