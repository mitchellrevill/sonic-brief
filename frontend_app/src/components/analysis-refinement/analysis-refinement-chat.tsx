import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  useAnalysisRefinementMutation, 
  getRefinementHistoryQuery, 
  getRefinementSuggestionsQuery 
} from "@/queries/audio-recordings.query";
import { useQuery } from "@tanstack/react-query";
import {
  Send,
  Bot,
  User as UserIcon,
  Loader2,
  MessageSquare,
  Sparkles,
  RefreshCw,
  AlertCircle,
  ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface AnalysisRefinementChatProps {
  jobId: string;
  className?: string;
}

interface RefinementMessage {
  id: string;
  role: "user" | "assistant";
  message: string;
  timestamp: string;
}

export function AnalysisRefinementChat({ jobId, className }: AnalysisRefinementChatProps) {
  const [inputMessage, setInputMessage] = useState("");
  const [isExpanded, setIsExpanded] = useState(true); // Start expanded in modal
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Queries for chat history and suggestions
  const {
    data: historyResponse,
    isLoading: isLoadingHistory,
    error: historyError,
    refetch: refetchHistory,
  } = useQuery(getRefinementHistoryQuery(jobId));

  const {
    data: suggestionsResponse,
  } = useQuery(getRefinementSuggestionsQuery(jobId));

  // Extract arrays from API responses
  const chatHistory = historyResponse?.history || [];
  const suggestions = suggestionsResponse?.suggestions || [];

  // Convert API history entries to display format
  const displayMessages: RefinementMessage[] = chatHistory.flatMap((entry) => [
    {
      id: `${entry.id}-user`,
      role: "user" as const,
      message: entry.user_message,
      timestamp: new Date(entry.timestamp * 1000).toISOString(),
    },
    {
      id: `${entry.id}-assistant`,
      role: "assistant" as const,
      message: entry.ai_response,
      timestamp: new Date(entry.timestamp * 1000).toISOString(),
    },
  ]);
  const refinementMutation = useAnalysisRefinementMutation();
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [displayMessages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);  const handleSendMessage = async (message: string) => {
    if (!message.trim() || refinementMutation.isPending) return;

    try {
      // Auto-expand if not already expanded
      if (!isExpanded) {
        setIsExpanded(true);
      }

      await refinementMutation.mutateAsync({
        jobId,
        request: { user_request: message.trim() }
      });
      setInputMessage("");
      // Refresh chat history after sending message
      refetchHistory();
      toast.success("Message sent successfully");
    } catch (error) {
      console.error("Failed to send message:", error);
      toast.error("Failed to send message. Please try again.");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputMessage);
  };
  const handleSuggestionClick = (suggestion: string) => {
    setInputMessage(suggestion);
    // Auto-expand when user clicks a suggestion
    if (!isExpanded) {
      setIsExpanded(true);
    }
    inputRef.current?.focus();
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return '';
    }
  };
  if (historyError) {
    return (
      <div className={cn("w-full border rounded-lg bg-card", className)}>
        <div className="p-4">
          <div className="flex flex-col items-center justify-center py-6 space-y-3">
            <div className="rounded-full bg-destructive/10 p-2">
              <AlertCircle className="h-4 w-4 text-destructive" />
            </div>
            <div className="text-center space-y-1">
              <h3 className="font-medium text-sm">Failed to load chat history</h3>
              <p className="text-xs text-muted-foreground">
                There was an error loading the refinement chat. Please try again.
              </p>
            </div>
            <Button onClick={() => refetchHistory()} variant="outline" size="sm">
              <RefreshCw className="mr-1.5 h-3 w-3" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }return (
    <div className={cn("w-full border rounded-lg bg-card transition-all duration-300", className)}>
      {/* Compact Header */}
      <div 
        className="px-4 py-3 border-b cursor-pointer hover:bg-muted/30 transition-colors flex items-center gap-2"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="bg-primary/10 rounded-full p-1.5">
          <Sparkles className="text-primary h-3.5 w-3.5" />
        </span>
        <span className="font-medium text-sm">Analysis Refinement</span>
        {displayMessages.length > 0 && (
          <Badge variant="secondary" className="ml-auto text-xs px-2 py-0.5">
            {chatHistory.length}
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="ml-1 h-5 w-5 transition-transform duration-300"
          style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Collapsed Preview */}
      {!isExpanded && chatHistory.length > 0 && (
        <div className="px-4 py-2 text-xs text-muted-foreground border-b bg-muted/20">
          <div className="flex items-center justify-between">
            <span>{chatHistory.length} message{chatHistory.length !== 1 ? 's' : ''} • Click to expand</span>
            <span>Latest: {new Date(chatHistory[chatHistory.length - 1]?.timestamp * 1000).toLocaleDateString()}</span>
          </div>
        </div>
      )}      {/* Collapsed Quick Input */}
      {!isExpanded && (
        <div className="px-4 py-3">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Quick question about your analysis..."
              disabled={refinementMutation.isPending}
              className="flex-1 text-sm h-8"
              maxLength={1000}
              onFocus={() => setIsExpanded(true)}
            />
            <Button 
              type="submit" 
              size="sm"
              disabled={!inputMessage.trim() || refinementMutation.isPending}
              className="h-8 px-3"
            >
              {refinementMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Send className="h-3 w-3" />
              )}
            </Button>
          </form>
        </div>
      )}      {isExpanded && (
        <div className="flex-1 flex flex-col animate-in slide-in-from-top duration-300">
          {/* Suggestion Chips */}
          {suggestions.length > 0 && chatHistory.length === 0 && (
            <div className="px-4 py-3 space-y-3 border-b">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <MessageSquare className="h-3 w-3" />
                Suggested prompts:
              </div>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((suggestion, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    className="h-auto py-1.5 px-2.5 text-left justify-start text-wrap text-xs"
                    onClick={() => handleSuggestionClick(suggestion)}
                    disabled={refinementMutation.isPending}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          )}          {/* Chat Messages - Compact scrolling area */}
          <div className="flex-1 px-4">
            {isLoadingHistory ? (
              <div className="flex flex-col items-center justify-center py-6 space-y-3">
                <div className="rounded-full bg-primary/10 p-2 animate-pulse">
                  <Loader2 className="h-4 w-4 text-primary animate-spin" />
                </div>
                <div className="text-center space-y-1">
                  <h3 className="font-medium text-sm">Loading chat history...</h3>
                  <p className="text-xs text-muted-foreground">
                    Please wait while we fetch your conversation
                  </p>
                </div>
              </div>
            ) : chatHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-6 space-y-3">
                <div className="rounded-full bg-muted p-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-center space-y-1">
                  <h3 className="font-medium text-sm">Start refining your analysis</h3>
                  <p className="text-xs text-muted-foreground max-w-sm">
                    Ask questions about your analysis, request specific insights, or explore different perspectives.
                  </p>
                </div>
              </div>
            ) : (
              <ScrollArea className="h-[400px] pr-2" ref={scrollAreaRef}>
                <div className="space-y-2 py-2">
                  {displayMessages.map((message: RefinementMessage) => (
                    <div
                      key={message.id}
                      className={cn(
                        "flex gap-2 animate-in fade-in duration-300",
                        message.role === "user" ? "justify-end" : "justify-start"
                      )}
                    >
                      {message.role === "assistant" && (
                        <div className="rounded-full bg-primary/10 p-1 self-start mt-0.5 flex-shrink-0">
                          <Bot className="h-2.5 w-2.5 text-primary" />
                        </div>
                      )}
                      
                      <div className={cn(
                        "max-w-[75%] rounded-lg px-2.5 py-1.5 space-y-0.5",
                        message.role === "user" 
                          ? "bg-primary text-primary-foreground ml-6" 
                          : "bg-muted mr-6"
                      )}>
                        <div className="text-xs leading-relaxed whitespace-pre-wrap">
                          {message.message}
                        </div>
                        <div className={cn(
                          "text-[10px]",
                          message.role === "user" 
                            ? "text-primary-foreground/60" 
                            : "text-muted-foreground"
                        )}>
                          {formatTimestamp(message.timestamp)}
                        </div>
                      </div>

                      {message.role === "user" && (
                        <div className="rounded-full bg-primary/10 p-1 self-start mt-0.5 flex-shrink-0">
                          <UserIcon className="h-2.5 w-2.5 text-primary" />
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {/* Loading indicator for pending message */}
                  {refinementMutation.isPending && (
                    <div className="flex gap-2 justify-start animate-in fade-in duration-300">
                      <div className="rounded-full bg-primary/10 p-1 self-start mt-0.5 flex-shrink-0">
                        <Bot className="h-2.5 w-2.5 text-primary" />
                      </div>
                      <div className="max-w-[75%] rounded-lg px-2.5 py-1.5 bg-muted mr-6">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Loader2 className="h-2.5 w-2.5 animate-spin" />
                          Analyzing your request...
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>
            )}
          </div>          {/* Input Form - Compact */}
          <div className="px-4 py-3 border-t border-border/30">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask questions about your analysis..."
                disabled={refinementMutation.isPending}
                className="flex-1 text-sm h-8"
                maxLength={1000}
              />
              <Button 
                type="submit" 
                size="sm"
                disabled={!inputMessage.trim() || refinementMutation.isPending}
                className="h-8 px-3"
              >
                {refinementMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Send className="h-3 w-3" />
                )}
              </Button>
            </form>
            
            {/* Character count */}
            {inputMessage.length > 800 && (
              <div className="text-[10px] text-muted-foreground mt-1 text-right">
                {inputMessage.length}/1000 characters
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
