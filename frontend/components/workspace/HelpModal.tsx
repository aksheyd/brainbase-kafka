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
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>How Kafka Works</DialogTitle>
          <DialogDescription>
            Create and modify AI agents using natural language.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4 text-sm">
          <div className="grid gap-1">
            <h4 className="font-medium">1. Creating Your First Agent</h4>
            <p className="text-muted-foreground">
              Start with an empty editor or select 'agent.based'. Describe the agent you want to create in the prompt bar below (e.g., "Create a simple chatbot that greets the user"). Kafka will generate the initial code for you.
            </p>
          </div>
          <div className="grid gap-1">
            <h4 className="font-medium">2. Modifying Your Agent</h4>
            <p className="text-muted-foreground">
              Once you have code, describe the changes you want to make (e.g., "Change the greeting message", "Add a function to ask for the user's name"). Kafka will generate a diff showing the proposed changes.
            </p>
          </div>
           <div className="grid gap-1">
            <h4 className="font-medium">3. Applying Changes (Diffs)</h4>
            <p className="text-muted-foreground">
              Review the suggested changes in the diff viewer. If you like them, click "Accept" to apply the changes to your code. If not, click "Reject" or simply describe further modifications.
            </p>
          </div>
           <div className="grid gap-1">
            <h4 className="font-medium">Adding Context</h4>
            <p className="text-muted-foreground">
              Use the "Add context" button to provide additional information or examples to help the AI better understand your request, especially for complex changes.
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