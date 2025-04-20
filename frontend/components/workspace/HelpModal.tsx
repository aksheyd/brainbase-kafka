'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose, // Added for close button
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface HelpModalProps {
  children: React.ReactNode; // The trigger element (e.g., the Help button)
}

export function HelpModal({ children }: HelpModalProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] z-[60]">
        <DialogHeader>
          <DialogTitle>How Kafka Works</DialogTitle>
          <DialogDescription>
            Vibe-code your AI agents using natural language.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4 text-sm">
          <div className="grid gap-1">
            <h4 className="font-medium">1. Creating Your First Agent</h4>
            <p className="text-muted-foreground">
              Simply describe the agent you want to create in the prompt bar below (e.g., "Create a simple chatbot that greets the user"). Kafka will automatically generate the `.based` file for you, named based on your description.
            </p>
          </div>
          <div className="grid gap-1">
            <h4 className="font-medium">2. Modifying Your Agent</h4>
            <p className="text-muted-foreground">
              With a file open, describe the changes you want (e.g., "Change the greeting message", "Add a function to ask for the user's name"). Kafka will generate a diff (code changes) for the active file.
            </p>
          </div>
           <div className="grid gap-1">
            <h4 className="font-medium">3. Applying Changes (Diffs)</h4>
            <p className="text-muted-foreground">
              Review the suggested changes in the diff viewer. Click "Accept" to apply them to your code, or "Reject" to discard them. You can then refine your request in the prompt bar.
            </p>
          </div>
           <div className="grid gap-1">
             <h4 className="font-medium">4. Creating Additional Files</h4>
             <p className="text-muted-foreground">
               To create more files for organization (e.g., utility functions, different agent parts), explicitly ask in the prompt: "Create a new file for database utilities" or "Make an agent file to handle user profiles". Kafka will create and name the new file.
             </p>
          </div>
           <div className="grid gap-1">
            <h4 className="font-medium">Adding Context</h4>
            <p className="text-muted-foreground">
              Use the "Add context" button to provide extra details, examples, or instructions to help the AI better understand your requests, especially for complex changes or new files.
            </p>
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
             <Button type="button" variant="secondary">
                Got it!
             </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
} 