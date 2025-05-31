import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
  }, []);
  const handleSendMessage = async (message: string) => {
    if (!message.trim() || refinementMutation.isPending) return;

    try {
      await refinementMutation.mutateAsync({
        jobId,
        request: { message: message.trim() }
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
      <Card className={cn("w-full", className)}>
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <div className="rounded-full bg-destructive/10 p-3">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <div className="text-center space-y-2">
              <h3 className="font-medium">Failed to load chat history</h3>
              <p className="text-sm text-muted-foreground">
                There was an error loading the refinement chat. Please try again.
              </p>
            </div>
            <Button onClick={() => refetchHistory()} variant="outline">
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full flex flex-col", className)}>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          <span className="bg-primary/10 rounded-full p-2">
            <Sparkles className="text-primary h-4 w-4" />
          </span>          Analysis Refinement
          {displayMessages.length > 0 && (
            <Badge variant="secondary" className="ml-auto">
              {chatHistory.length} conversation{chatHistory.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4 p-0 pb-6">        {/* Suggestion Chips */}
        {suggestions.length > 0 && chatHistory.length === 0 && (
          <div className="px-6 space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <MessageSquare className="h-4 w-4" />
              Suggested prompts to get started:
            </div>            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="h-auto py-2 px-3 text-left justify-start text-wrap"
                  onClick={() => handleSuggestionClick(suggestion)}
                  disabled={refinementMutation.isPending}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
            <Separator />
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 min-h-[300px] px-6">
          {isLoadingHistory ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <div className="rounded-full bg-primary/10 p-3 animate-pulse">
                <Loader2 className="h-6 w-6 text-primary animate-spin" />
              </div>
              <div className="text-center space-y-2">
                <h3 className="font-medium">Loading chat history...</h3>
                <p className="text-sm text-muted-foreground">
                  Please wait while we fetch your conversation
                </p>
              </div>
            </div>
          ) : chatHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <div className="rounded-full bg-muted p-3">
                <MessageSquare className="h-6 w-6 text-muted-foreground" />
              </div>
              <div className="text-center space-y-2">
                <h3 className="font-medium">Start refining your analysis</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  Ask questions about your analysis, request specific insights, or explore different perspectives. 
                  Try using one of the suggested prompts above!
                </p>
              </div>
            </div>
          ) : (            <ScrollArea className="h-[400px] pr-4" ref={scrollAreaRef}>
              <div className="space-y-4">
                {displayMessages.map((message: RefinementMessage) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex gap-3 animate-in fade-in duration-500",
                      message.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {message.role === "assistant" && (
                      <div className="rounded-full bg-primary/10 p-2 self-start mt-1">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    )}
                    
                    <div className={cn(
                      "max-w-[80%] rounded-lg px-4 py-3 space-y-1",
                      message.role === "user" 
                        ? "bg-primary text-primary-foreground ml-12" 
                        : "bg-muted mr-12"
                    )}>
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">
                        {message.message}
                      </div>
                      <div className={cn(
                        "text-xs",
                        message.role === "user" 
                          ? "text-primary-foreground/70" 
                          : "text-muted-foreground"
                      )}>
                        {formatTimestamp(message.timestamp)}
                      </div>
                    </div>

                    {message.role === "user" && (
                      <div className="rounded-full bg-primary/10 p-2 self-start mt-1">
                        <UserIcon className="h-4 w-4 text-primary" />
                      </div>
                    )}
                  </div>
                ))}
                
                {/* Loading indicator for pending message */}
                {refinementMutation.isPending && (
                  <div className="flex gap-3 justify-start animate-in fade-in duration-500">
                    <div className="rounded-full bg-primary/10 p-2 self-start mt-1">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="max-w-[80%] rounded-lg px-4 py-3 bg-muted mr-12">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Analyzing your request...
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Input Form */}
        <div className="px-6 pt-4 border-t border-border/50">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask questions about your analysis or request specific insights..."
              disabled={refinementMutation.isPending}
              className="flex-1"
              maxLength={1000}
            />
            <Button 
              type="submit" 
              disabled={!inputMessage.trim() || refinementMutation.isPending}
              className="transition-all duration-200 hover:scale-105"
            >
              {refinementMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
          
          {/* Character count */}
          {inputMessage.length > 800 && (
            <div className="text-xs text-muted-foreground mt-1 text-right">
              {inputMessage.length}/1000 characters
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
