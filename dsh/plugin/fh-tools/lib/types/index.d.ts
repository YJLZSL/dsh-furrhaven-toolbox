import { defineTool } from '@deepseek-ai/dsh-tools';
export declare const name = "@dsh-external/dsh-fh-tools";
export declare const inject: string[];
export declare function apply(ctx: {
    effect: (fn: () => void, label?: string) => void;
    tools: {
        register: (tool: ReturnType<typeof defineTool>, label?: string) => void;
    };
    skills?: {
        register: (skill: {
            name: string;
            description: string;
            content: string;
            whenToUse?: string;
        }) => () => void;
    };
}): void;
