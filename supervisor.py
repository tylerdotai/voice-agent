#!/usr/bin/env python3
"""
Supervisor UI - Human-in-the-Loop control for Dexter Voice Agent.
Story 12: Human-in-the-Loop Interrupt Supervision.
"""
import sys
import signal

class Supervisor:
    def __init__(self):
        self.agent_state = "idle"
        self.interrupted = False
    
    def print_status(self):
        print("\n" + "="*50)
        print("  DEXTER VOICE AGENT - SUPERVISOR")
        print("="*50)
        print(f"  Agent State: {self.agent_state}")
        print(f"  Interrupted: {self.interrupted}")
        print("="*50)
        print("  Controls:")
        print("    [A] Approve - Allow agent to continue")
        print("    [M] Modify - Modify agent behavior")
        print("    [I] Interrupt - Stop agent mid-turn")
        print("    [Q] Quit - Exit supervisor")
        print("="*50)
    
    def run(self):
        signal.signal(signal.SIGINT, lambda s,f: sys.exit(0))
        
        while True:
            self.print_status()
            try:
                cmd = input("\n> ").strip().lower()
                if cmd == 'a':
                    print("✓ Approved - agent continuing")
                    self.interrupted = False
                elif cmd == 'm':
                    print("! Modify mode - enter new instruction:")
                    # Would modify agent behavior here
                elif cmd == 'i':
                    print("⚠ Interrupted - agent paused")
                    self.interrupted = True
                elif cmd == 'q':
                    print("Goodbye!")
                    break
            except (EOFError, KeyboardInterrupt):
                break

if __name__ == "__main__":
    print("Starting Dexter Supervisor...")
    sup = Supervisor()
    sup.run()
