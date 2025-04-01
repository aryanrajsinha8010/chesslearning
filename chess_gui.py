import tkinter as tk
from tkinter import ttk, messagebox
import chess
import threading
import sys
import random
import os
from typing import Optional, List, Tuple, Dict, Any, Callable

from chess_game import ChessGame

class ChessGUI:
    """GUI implementation for the chess learning platform."""
    
    def __init__(self, master: tk.Tk, game: ChessGame, human_is_white: bool):
        """Initialize the chess GUI.
        
        Args:
            master: The Tkinter root window
            game: The ChessGame instance
            human_is_white: Whether the human player is playing as white
        """
        self.master = master
        self.game = game
        self.human_is_white = human_is_white
        self.square_size = 80
        self.selected_piece = None
        self.legal_moves = []
        self.flipped = False
        self.hint_arrows = []
        self.last_hint = None
        self._board_needs_update = True
        self.practice_mode = game.mode == "Practice"
        self.self_practice_mode = game.mode == "Self-Practice"
        
        # Map of piece types to unicode characters for rendering
        self.piece_chars = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }
        
        # Colors for the board and pieces
        self.colors = {
            'light_square': '#EEEED2',
            'dark_square': '#769656',
            'selected': '#BACA2B',
            'legal_move': '#F7F769',
            'last_move': '#BABABA',
            'white_piece': '#FFFFFF',
            'black_piece': '#000000',
            'hint_arrow': 'blue'
        }
        
        # Setup the UI
        self.setup_ui()
        
        # If computer plays white, make first move
        if not human_is_white and not self.self_practice_mode:
            self.engine_move()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Configure main window
        self.master.title("Chess Learning Platform")
        self.master.geometry("1100x750")
        self.master.minsize(900, 650)
        
        # Main frame
        self.main_frame = tk.Frame(self.master, bg='#5A2A0D')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Board frame
        self.board_frame = tk.Frame(self.main_frame, bg='#5A2A0D')
        self.board_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Info frame (right side)
        self.info_frame = tk.Frame(self.main_frame, width=300, bg='#5A2A0D')
        self.info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        # Chess board
        self.canvas = tk.Canvas(self.board_frame, width=8*self.square_size, 
                              height=8*self.square_size, highlightthickness=0)
        self.canvas.pack(pady=10)
        
        # Control panel below board
        self.control_frame = tk.Frame(self.board_frame, bg='#5A2A0D')
        self.control_frame.pack(fill=tk.X, pady=5)
        
        # Control buttons
        self.create_control_buttons()
        
        # Status bar
        self.status_label = tk.Label(self.board_frame, text="White's turn", 
                                   font=('Arial', 14), bg='#5A2A0D', fg='white')
        self.status_label.pack()
        
        # Information panel
        self.create_info_panel()
        
        # Event bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.master.bind("<Configure>", self.on_window_resize)
        
        # Initial draw
        self.update_display()
    
    def create_control_buttons(self):
        """Create control buttons for the chess interface."""
        tk.Button(self.control_frame, text="Flip Board", command=self.flip_board,
                bg='#8B4513', fg='white').pack(side=tk.LEFT, padx=5)
        
        self.hint_var = tk.BooleanVar(value=self.game.show_hints)
        tk.Checkbutton(self.control_frame, text="Show Hints", variable=self.hint_var,
                     command=self.toggle_hints, bg='#5A2A0D', fg='white',
                     selectcolor='#5A2A0D').pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.control_frame, text="Hint", command=self.show_hint,
                bg='#8B4513', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.control_frame, text="Take Back", command=self.take_back_move,
                bg='#8B4513', fg='white').pack(side=tk.LEFT, padx=5)
        
        # Difficulty selector
        tk.Label(self.control_frame, text="Difficulty:", bg='#5A2A0D', fg='white').pack(side=tk.RIGHT)
        self.difficulty_var = tk.StringVar(value=str(self.game.difficulty_level))
        difficulty_menu = tk.OptionMenu(self.control_frame, self.difficulty_var, *[1,2,3,4],
                                     command=self.change_difficulty)
        difficulty_menu.config(bg='#8B4513', fg='white')
        difficulty_menu.pack(side=tk.RIGHT, padx=5)
        
        # Add new buttons for practice mode
        if self.practice_mode:
            tk.Button(self.control_frame, text="Suggest Move", command=self.suggest_move,
                    bg='#8B4513', fg='white').pack(side=tk.LEFT, padx=5)
            tk.Button(self.control_frame, text="Coach Comment", command=self.show_coach_comment,
                    bg='#8B4513', fg='white').pack(side=tk.LEFT, padx=5)
        
        # Add new button for Self-Practice mode
        if self.self_practice_mode:
            tk.Button(self.control_frame, text="Suggest Move", command=self.suggest_move,
                    bg='#8B4513', fg='white').pack(side=tk.LEFT, padx=5)
    
    def create_info_panel(self):
        """Create the information panel on the right side."""
        info_panel = tk.Frame(self.info_frame, bg='#8B4513', bd=2, relief=tk.RIDGE)
        info_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Move explanation area
        explanation_frame = tk.Frame(info_panel, bg='#8B4513')
        explanation_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(explanation_frame, text="Move Analysis", font=('Arial', 12, 'bold'), 
                bg='#8B4513', fg='white').pack(anchor=tk.W)
        
        self.explanation_label = tk.Label(explanation_frame, text="Welcome to Chess!\n\nYour move...", 
                                        font=('Arial', 11), bg='#8B4513', fg='white',
                                        justify=tk.LEFT, wraplength=280)
        self.explanation_label.pack(fill=tk.X, pady=5)
        
        # Evaluation frame
        eval_frame = tk.Frame(info_panel, bg='#8B4513')
        eval_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(eval_frame, text="Position Evaluation", font=('Arial', 12, 'bold'), 
                bg='#8B4513', fg='white').pack(anchor=tk.W)
        
        self.eval_label = tk.Label(eval_frame, text="Evaluation: 0.0", 
                                  font=('Arial', 11), bg='#8B4513', fg='white')
        self.eval_label.pack(anchor=tk.W)
        
        # Move history
        history_frame = tk.Frame(info_panel, bg='#8B4513')
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(history_frame, text="Move History", font=('Arial', 12, 'bold'), 
                bg='#8B4513', fg='white').pack(anchor=tk.W)
        
        scrollbar = tk.Scrollbar(history_frame)
        self.move_history = tk.Listbox(history_frame, width=30, height=15, 
                                     font=('Arial', 10), bg='#D2B48C', fg='black',
                                     yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.move_history.yview)
        
        self.move_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def on_window_resize(self, event):
        """Handle window resize events to adjust the chess board size."""
        if event.widget == self.master:
            # Only process if main window was resized
            board_width = self.board_frame.winfo_width() - 20  # Adjust for padding
            board_height = self.board_frame.winfo_height() - 100  # Adjust for other widgets
            
            new_size = min(board_width // 8, board_height // 8)
            
            if new_size > 40 and new_size != self.square_size:  # Minimum square size
                self.square_size = new_size
                self.canvas.config(width=8*self.square_size, height=8*self.square_size)
                self._board_needs_update = True
                self.update_display()
    
    def flip_board(self):
        """Flip the board view."""
        self.flipped = not self.flipped
        self.selected_piece = None
        self.clear_highlights()
        self._board_needs_update = True
        self.update_display()
        self.update_explanation("Board flipped")
    
    def toggle_hints(self):
        """Toggle hint display on/off."""
        self.game.show_hints = self.hint_var.get()
        if self.game.show_hints and self.is_human_turn():
            self.show_hint()
        else:
            self.clear_hints()
        self.update_explanation("Hints " + ("enabled" if self.game.show_hints else "disabled"))
    
    def change_difficulty(self, level):
        """Change the engine difficulty level."""
        self.game.set_difficulty(int(level))
        self.update_explanation(f"Difficulty set to level {level}")
    
    def take_back_move(self):
        """Undo the last move(s)."""
        if self.game.mode == "Play":
            # In Play mode, take back both the engine's move and the human's move
            self.game.undo_move()  # Take back engine move
            self.game.undo_move()  # Take back human move
        else:
            # In other modes, just take back the last move
            self.game.undo_move()
        
        self.selected_piece = None
        self.clear_highlights()
        self._board_needs_update = True
        self.update_move_history()
        self.update_status()
        self.update_display()
        self.update_explanation("Move undone")
    
    def suggest_move(self):
        """Suggest a move in practice mode."""
        if self.game.board.is_game_over():
            self.update_explanation("Game is over")
            return
        
        best_move = self.game.get_practice_move()
        if best_move:
            self.clear_hints()
            self.last_hint = best_move
            self.draw_arrow(best_move.from_square, best_move.to_square, "blue")
            explanation = self.generate_move_explanation(best_move)
            self.update_explanation("Suggested move: " + explanation)
    
    def show_coach_comment(self):
        """Show coaching comments for the last move."""
        if not self.game.last_move:
            self.update_explanation("No moves to comment on yet")
            return
        
        comment = self.game.get_coach_comment(self.game.last_move)
        self.update_explanation("Coach says: " + comment)
    
    def show_hint(self):
        """Show a hint for the current position."""
        if self.game.board.is_game_over() or not self.is_human_turn():
            return
        
        self.clear_hints()
        best_move = self.game.get_engine_move()
        if best_move:
            self.last_hint = best_move
            self.draw_arrow(best_move.from_square, best_move.to_square, "blue")
            explanation = self.generate_move_explanation(best_move)
            self.update_explanation("Hint: " + explanation)
    
    def generate_move_explanation(self, move):
        """Generate an explanation for a chess move."""
        piece = self.game.board.piece_at(move.from_square)
        if not piece:
            return "Invalid move"
        
        piece_name = chess.piece_name(piece.piece_type).capitalize()
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)
        
        explanation = f"{piece_name} from {from_sq} to {to_sq}"
        
        # Check if move is a capture
        if self.game.board.is_capture(move):
            captured = self.game.board.piece_at(move.to_square)
            if captured:
                captured_name = chess.piece_name(captured.piece_type)
                explanation += f", capturing {captured_name}"
        
        # Check if move gives check
        board_copy = self.game.board.copy()
        board_copy.push(move)
        if board_copy.is_check():
            explanation += ", giving check"
        
        return explanation
    
    def clear_highlights(self):
        """Clear all highlighted squares on the board."""
        self.legal_moves = []
        self.update_display()
    
    def clear_hints(self):
        """Clear hint arrows from the board."""
        self.hint_arrows = []
        self.update_display()
    
    def update_explanation(self, text):
        """Update the explanation text in the UI."""
        self.explanation_label.config(text=text)
    
    def update_evaluation(self):
        """Update the position evaluation display."""
        evaluation = self.game.analyze_position()
        self.eval_label.config(text=f"Evaluation: {evaluation}")
    
    def update_move_history(self):
        """Update the move history display."""
        self.move_history.delete(0, tk.END)
        
        # Display moves in proper format (number. white_move black_move)
        move_pairs = []
        for i, move in enumerate(self.game.move_history):
            if i % 2 == 0:
                # White's move
                move_number = i // 2 + 1
                move_pairs.append(f"{move_number}. {move}")
            else:
                # Black's move - append to the last item
                move_pairs[-1] += f" {move}"
        
        for move_pair in move_pairs:
            self.move_history.insert(tk.END, move_pair)
        
        # Ensure the last move is visible
        if move_pairs:
            self.move_history.see(tk.END)
    
    def update_status(self):
        """Update the status display with game state information."""
        board = self.game.board
        
        if board.is_checkmate():
            result = "Black wins" if board.turn == chess.WHITE else "White wins"
            self.status_label.config(text=f"Checkmate! {result}")
        elif board.is_stalemate():
            self.status_label.config(text="Stalemate! Game drawn")
        elif board.is_insufficient_material():
            self.status_label.config(text="Insufficient material! Game drawn")
        elif board.is_check():
            side = "White" if board.turn == chess.WHITE else "Black"
            self.status_label.config(text=f"{side} is in check")
        else:
            side = "White" if board.turn == chess.WHITE else "Black"
            self.status_label.config(text=f"{side}'s turn")
    
    def is_human_turn(self):
        """Check if it's the human player's turn."""
        if self.self_practice_mode:
            # In self-practice mode, human plays both sides
            return True
        
        is_white_turn = self.game.board.turn == chess.WHITE
        return (self.human_is_white and is_white_turn) or (not self.human_is_white and not is_white_turn)
    
    def on_click(self, event):
        """Handle mouse clicks on the chess board."""
        if self.game.board.is_game_over() or not self.is_human_turn():
            return
        
        # Calculate board coordinates from pixel coordinates
        col = event.x // self.square_size
        row = event.y // self.square_size
        
        # Adjust for board orientation
        if self.flipped:
            col = 7 - col
            row = 7 - row
        else:
            row = 7 - row
        
        square = chess.square(col, row)
        
        # Handle piece selection or move
        piece = self.game.board.piece_at(square)
        
        if self.selected_piece is not None:
            # If a piece is already selected, try to move it
            move = chess.Move(self.selected_piece, square)
            
            # Check if promotion is needed
            if piece_at_selected := self.game.board.piece_at(self.selected_piece):
                if piece_at_selected.piece_type == chess.PAWN:
                    # Check if pawn reaches the last rank
                    if (row == 7 and piece_at_selected.color == chess.WHITE) or \
                       (row == 0 and piece_at_selected.color == chess.BLACK):
                        move = chess.Move(self.selected_piece, square, promotion=chess.QUEEN)
            
            # Try to make the move
            if move in self.game.board.legal_moves:
                self.make_move(move)
            else:
                # If move is not legal, check if clicked on another own piece
                if piece and piece.color == self.game.board.turn:
                    # Select the new piece
                    self.selected_piece = square
                    self.legal_moves = [move.to_square for move in self.game.board.legal_moves 
                                      if move.from_square == square]
                    self.update_display()
                else:
                    # Deselect if clicked on empty square or opponent's piece
                    self.selected_piece = None
                    self.legal_moves = []
                    self.update_display()
        else:
            # No piece selected yet
            if piece and piece.color == self.game.board.turn:
                self.selected_piece = square
                self.legal_moves = [move.to_square for move in self.game.board.legal_moves 
                                  if move.from_square == square]
                self.update_display()
    
    def make_move(self, move):
        """Make a move and handle game state updates."""
        san_move = self.game.board.san(move)
        self.game.make_move(move)
        
        self.selected_piece = None
        self.legal_moves = []
        self.clear_hints()
        self._board_needs_update = True
        
        self.update_move_history()
        self.update_status()
        self.update_evaluation()
        self.update_display()
        
        # Update explanation with the move that was made
        explanation = self.generate_move_explanation(move)
        self.update_explanation(f"You played: {explanation}")
        
        # If not game over and not in self-practice mode, make engine move
        if not self.game.board.is_game_over() and self.game.mode == "Play":
            self.master.after(500, self.engine_move)  # Delay for better UX
    
    def engine_move(self):
        """Make a move with the chess engine."""
        if self.game.board.is_game_over():
            return
        
        # Get engine move
        engine_move = self.game.get_engine_move()
        if not engine_move:
            return
        
        # Make the move
        san_move = self.game.board.san(engine_move)
        self.game.make_move(engine_move)
        
        self._board_needs_update = True
        self.update_move_history()
        self.update_status()
        self.update_evaluation()
        self.update_display()
        
        # Highlight the engine's move
        from_sq = engine_move.from_square
        to_sq = engine_move.to_square
        self.highlight_last_move(from_sq, to_sq)
        
        # Update explanation with engine's move
        explanation = self.generate_move_explanation(engine_move)
        self.update_explanation(f"Engine played: {explanation}")
    
    def highlight_last_move(self, from_square, to_square):
        """Highlight the last move made on the board."""
        # Will be implemented in the update_display method
        self.game.last_move = chess.Move(from_square, to_square)
        self.update_display()
    
    def draw_arrow(self, from_square, to_square, color):
        """Draw an arrow on the board to indicate a suggested move."""
        self.hint_arrows.append((from_square, to_square, color))
        self.update_display()
    
    def update_display(self):
        """Update the chess board display."""
        if not self._board_needs_update and not self.legal_moves and not self.hint_arrows and not self.game.last_move:
            return  # No need to redraw
        
        self._board_needs_update = False
        self.canvas.delete("all")
        
        # Draw board squares
        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = (7 - row) * self.square_size if not self.flipped else row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                
                # Determine square color
                is_light = (row + col) % 2 == 0
                color = self.colors['light_square'] if is_light else self.colors['dark_square']
                
                # Highlight selected square
                square = chess.square(col, row if not self.flipped else 7 - row)
                if self.selected_piece == square:
                    color = self.colors['selected']
                # Highlight legal moves
                elif square in self.legal_moves:
                    color = self.colors['legal_move']
                # Highlight last move
                elif self.game.last_move and (square == self.game.last_move.from_square or 
                                          square == self.game.last_move.to_square):
                    color = self.colors['last_move']
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='')
                
                # Draw coordinate labels
                if col == 0:  # Left edge - row numbers
                    text_y = y1 + self.square_size // 2
                    label = str(row + 1) if not self.flipped else str(8 - row)
                    self.canvas.create_text(5, text_y, text=label, anchor=tk.W, 
                                          font=('Arial', 10), fill='black' if is_light else 'white')
                
                if row == 7 if not self.flipped else row == 0:  # Bottom edge - column letters
                    text_x = x1 + self.square_size // 2
                    label = chr(97 + col)  # 'a' through 'h'
                    self.canvas.create_text(text_x, y2 - 5, text=label, anchor=tk.S, 
                                          font=('Arial', 10), fill='black' if is_light else 'white')
        
        # Draw pieces
        for square in chess.SQUARES:
            piece = self.game.board.piece_at(square)
            if piece:
                file_idx = chess.square_file(square)
                rank_idx = chess.square_rank(square)
                
                if self.flipped:
                    x = (7 - file_idx) * self.square_size + self.square_size // 2
                    y = rank_idx * self.square_size + self.square_size // 2
                else:
                    x = file_idx * self.square_size + self.square_size // 2
                    y = (7 - rank_idx) * self.square_size + self.square_size // 2
                
                piece_symbol = self.piece_chars[piece.symbol()]
                color = self.colors['white_piece'] if piece.color == chess.WHITE else self.colors['black_piece']
                
                self.canvas.create_text(x, y, text=piece_symbol, font=('Arial', self.square_size//2), 
                                      fill=color, tags="piece")
        
        # Draw hint arrows
        for from_square, to_square, color in self.hint_arrows:
            self.draw_arrow_on_canvas(from_square, to_square, color)
    
    def draw_arrow_on_canvas(self, from_square, to_square, color):
        """Draw an arrow between two squares on the canvas."""
        from_file = chess.square_file(from_square)
        from_rank = chess.square_rank(from_square)
        to_file = chess.square_file(to_square)
        to_rank = chess.square_rank(to_square)
        
        if self.flipped:
            from_x = (7 - from_file) * self.square_size + self.square_size // 2
            from_y = from_rank * self.square_size + self.square_size // 2
            to_x = (7 - to_file) * self.square_size + self.square_size // 2
            to_y = to_rank * self.square_size + self.square_size // 2
        else:
            from_x = from_file * self.square_size + self.square_size // 2
            from_y = (7 - from_rank) * self.square_size + self.square_size // 2
            to_x = to_file * self.square_size + self.square_size // 2
            to_y = (7 - to_rank) * self.square_size + self.square_size // 2
        
        # Draw arrow line
        self.canvas.create_line(from_x, from_y, to_x, to_y, 
                              fill=color, width=3, arrow=tk.LAST, arrowshape=(16, 20, 6))

