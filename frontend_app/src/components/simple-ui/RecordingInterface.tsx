import { useState, useRef, useEffect } from "react";
// Utility to detect iOS
function isIOS() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
}
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Mic, 
  Square, 
  Play, 
  Pause, 
  Upload, 
  ArrowLeft, 
  Clock,
  Check,
  AlertCircle,
  Eye,
  ChevronLeft,
  ChevronRight,
  MessageSquare
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { uploadFile, fetchAudioBlob } from "@/lib/api";
import { convertToWavWithFFmpeg } from "@/lib/ffmpegConvert";
import { toast } from "sonner";
import { recordingToasts, uploadToasts, fileToasts, storageToasts } from "@/lib/toast-utils";
import { useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchSubcategories, type SubcategoryResponse } from "@/api/prompt-management";
import { 
  saveDraftRecording, 
  getDraftRecording, 
  deleteDraftRecording,
  cleanupOldDrafts,
  checkStorageAndWarn,
  type DraftRecording 
} from "@/lib/draft-storage";
import { DraftRestorationBanner } from "@/components/ui/draft-restoration-banner";
import { useAudioAnalyzer } from "@/hooks/useAudioAnalyzer";
import { MinimalAudioIndicator } from "@/components/ui/minimal-audio-indicator";

interface RecordingInterfaceProps {
  categoryId: string;
  subcategoryId: string;
  categoryName: string;
  subcategoryName: string;
  preSessionData?: Record<string, any>;
  onBack: () => void;
  onUploadComplete: () => void;
}

export function RecordingInterface(props: RecordingInterfaceProps) {
  const { categoryId, subcategoryId, categoryName, subcategoryName, preSessionData = {}, onBack, onUploadComplete } = props;

  // All hooks must be called at the top, before any conditional returns
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  // FFmpeg conversion state
  const [isConverting, setIsConverting] = useState(false);
  const [conversionProgress, setConversionProgress] = useState(0);
  const [conversionStep, setConversionStep] = useState("");
  // Talking points state
  const [currentTalkingPointIndex, setCurrentTalkingPointIndex] = useState(0);
  // Draft recording state
  const [existingDraft, setExistingDraft] = useState<DraftRecording | null>(null);
  const [isRestoringDraft, setIsRestoringDraft] = useState(false);
  const [currentDraftId, setCurrentDraftId] = useState<string | null>(null);


  // Auto-save draft on page unload or visibility change
  useEffect(() => {
    // Set up listeners only once when component mounts
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // Use refs to check current state
      const currentlyRecording = isRecordingRef.current;
      const hasRecording = audioBlobRef.current || audioChunks.current.length > 0;
      
      if (!hasRecording) return;

      // Prevent the page from unloading immediately
      event.preventDefault();
      event.returnValue = 'You have an unsaved recording. It will be saved as a draft.';

      try {
        console.log('BeforeUnload: Attempting emergency save', { currentlyRecording, chunks: audioChunks.current.length });

        const blobToSave = audioBlobRef.current;
        if (blobToSave) {
          console.log('Emergency saving finalized blob (synchronous attempt)');
          saveDraftRecording({
            categoryId,
            subcategoryId,
            categoryName,
            subcategoryName,
            audioBlob: blobToSave,
            duration: recordingTime,
            preSessionData,
            mimeType: blobToSave.type,
          }).then(id => {
            console.log('Emergency save completed:', id);
          }).catch(err => {
            console.error('Emergency save failed:', err);
          });
        } else if (currentlyRecording && audioChunks.current.length > 0) {
          // Emergency save of partial recording
          console.log('Emergency saving partial recording from chunks');
          const partialBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
          saveDraftRecording({
            categoryId,
            subcategoryId,
            categoryName,
            subcategoryName,
            audioBlob: partialBlob,
            duration: recordingTime,
            preSessionData,
            mimeType: partialBlob.type,
          }).then(id => {
            console.log('Emergency partial save completed:', id);
          }).catch(err => {
            console.error('Emergency partial save failed:', err);
          });
        }
      } catch (error) {
        console.error('Failed emergency save on unload:', error);
      }
    };

    let lastSaveTime = 0;
    const handleVisibilityChange = async () => {
      if (document.visibilityState === 'hidden') {
        // Debounce to prevent multiple saves
        const now = Date.now();
        if (now - lastSaveTime < 5000) {
          console.log('Skipping visibility save - too soon since last save');
          return;
        }
        lastSaveTime = now;

        try {
          const currentlyRecording = isRecordingRef.current;
          console.log('Visibility hidden: Attempting background save', { currentlyRecording, chunks: audioChunks.current.length });

          const blobToSave = audioBlobRef.current;
          if (blobToSave) {
            console.log('Background saving finalized blob');
            const draftId = await saveDraftRecording({
              categoryId,
              subcategoryId,
              categoryName,
              subcategoryName,
              audioBlob: blobToSave,
              duration: recordingTime,
              preSessionData,
              mimeType: blobToSave.type,
            });
            setCurrentDraftId(draftId);
            console.log('Background save completed:', draftId);
          } else if (currentlyRecording && audioChunks.current.length > 0) {
            console.log('Background saving partial recording from chunks');
            const partialBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
            const draftId = await saveDraftRecording({
              categoryId,
              subcategoryId,
              categoryName,
              subcategoryName,
              audioBlob: partialBlob,
              duration: recordingTime,
              preSessionData,
              mimeType: partialBlob.type,
            });
            setCurrentDraftId(draftId);
            console.log('Background partial save completed:', draftId);
          }
        } catch (error) {
          console.error('Failed background save on visibility change:', error);
        }
      }
    };

    // Add event listeners
    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    console.log('Auto-save listeners set up (mount only)');

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      console.log('Auto-save listeners cleaned up');
    };
  }, []); // Empty deps - set up once on mount, listeners use refs/closures to access current state

  // Periodic auto-save while recording (but only save partial chunks, not finalized blob)
  useEffect(() => {
    if (!isRecording || isPaused) return;

    const interval = setInterval(async () => {
      try {
        // Save partial recording from current chunks
        if (audioChunks.current.length > 0) {
          const partialBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
          console.log(`Periodic auto-save: ${audioChunks.current.length} chunks, ${partialBlob.size} bytes`);
          
          // Save without toast to avoid spam
          try {
            const draftId = await saveDraftRecording({
              categoryId,
              subcategoryId,
              categoryName,
              subcategoryName,
              audioBlob: partialBlob,
              duration: recordingTime,
              preSessionData,
              mimeType: partialBlob.type,
            });
            setCurrentDraftId(draftId);
            console.log('Periodic auto-save completed:', draftId);
            console.log(`Periodic auto-save at ${recordingTime}s: ${draftId}`);
          } catch (error: any) {
            console.warn('Periodic auto-save failed:', error);
            console.log(`Periodic auto-save failed: ${String(error?.message ?? error)}`);
          }
        }
      } catch (error) {
        console.warn('Failed to create periodic auto-save blob:', error);
      }
    }, 30000); // Save every 30 seconds

    return () => clearInterval(interval);
  }, [isRecording, isPaused]); // Only depend on recording state, NOT recordingTime to avoid recreating interval

  // Fetch subcategory to get in-session talking points
  const { data: subcategories } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => fetchSubcategories(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const currentSubcategory = (subcategories as SubcategoryResponse[])?.find(sub => sub.id === subcategoryId);
  const inSessionTalkingPoints = currentSubcategory?.inSessionTalkingPoints || [];
  
  // Flatten talking points for easy navigation
  const allTalkingPoints = inSessionTalkingPoints.flatMap((section: any) => 
    section.fields || []
  );

  // Only log pre-session data in development and only when it changes
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.debug('Pre-session data received:', preSessionData);
    }
  }, [preSessionData]);

  // Initialize: Check for existing draft and cleanup old drafts
  useEffect(() => {
    console.debug('RecordingInterface mount/start for', { categoryId, subcategoryId });
    const initializeDrafts = async () => {
      try {
        // Cleanup old drafts in the background
        cleanupOldDrafts().catch(err => {
          console.warn('Failed to cleanup old drafts:', err);
        });

        // Check storage and warn if needed
        checkStorageAndWarn().catch(err => {
          console.warn('Failed to check storage:', err);
        });

        // Check for existing draft for this category/subcategory
        const draft = await getDraftRecording(categoryId, subcategoryId);
        if (draft) {
          setExistingDraft(draft);
          console.log('Found existing draft:', draft);
        }
      } catch (error) {
        console.error('Error initializing drafts:', error);
      }
    };

    initializeDrafts();
  }, [categoryId, subcategoryId]);

  const nextTalkingPoint = () => {
    if (currentTalkingPointIndex < allTalkingPoints.length - 1) {
      setCurrentTalkingPointIndex(prev => prev + 1);
    }
  };

  const prevTalkingPoint = () => {
    if (currentTalkingPointIndex > 0) {
      setCurrentTalkingPointIndex(prev => prev - 1);
    }
  };

  // TalkingPointsDisplay component
  const TalkingPointsDisplay = () => {
    if (!allTalkingPoints.length) return null;

    const currentPoint = allTalkingPoints[currentTalkingPointIndex];

    return (
      <Card className="mb-6 border-border bg-card backdrop-blur-sm border-2 shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm sm:text-base font-semibold">
              <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5 text-foreground" />
              <span className="truncate">
                Talking Points ({currentTalkingPointIndex + 1} of {allTalkingPoints.length})
              </span>
            </CardTitle>
            <div className="flex gap-1 sm:gap-2 flex-shrink-0">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-full border-border hover:bg-accent hover:border-border/60 transition-all duration-200 touch-manipulation"
                onClick={prevTalkingPoint}
                disabled={currentTalkingPointIndex === 0}
                aria-label="Previous talking point"
                style={{ touchAction: 'manipulation' }}
              >
                <ChevronLeft className="h-3 w-3 sm:h-4 sm:w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-full border-border hover:bg-accent hover:border-border/60 transition-all duration-200 touch-manipulation"
                onClick={nextTalkingPoint}
                disabled={currentTalkingPointIndex === allTalkingPoints.length - 1}
                aria-label="Next talking point"
                style={{ touchAction: 'manipulation' }}
              >
                <ChevronRight className="h-3 w-3 sm:h-4 sm:w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-3">
            <div className="font-semibold text-foreground">
              {currentPoint?.name || `Point ${currentTalkingPointIndex + 1}`}
            </div>
            <div className="text-foreground leading-relaxed">
              {currentPoint?.type === 'markdown' && currentPoint?.value ? (
                <MarkdownRenderer content={currentPoint.value} />
              ) : (
                currentPoint?.value || 'No content available'
              )}
            </div>
            {currentPoint?.type && currentPoint.type !== 'text' && (
              <Badge variant="secondary" className="text-xs">
                {currentPoint.type}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  const router = useRouter();
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Keep the finalized audio blob available so we can save it reliably
  const audioBlobRef = useRef<Blob | null>(null);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  // Track last save to prevent duplicate toasts
  const lastSaveTimeRef = useRef<number>(0);
  // Track recording state for event listeners
  const isRecordingRef = useRef<boolean>(false);

  // Audio analysis for real-time quality monitoring
  const audioMetrics = useAudioAnalyzer(isRecording ? streamRef.current : null);

  // Timer effect
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording, isPaused]);

  // Cleanup effect - ensure resources are released on unmount ONLY
  useEffect(() => {
    return () => {
      console.log('RecordingInterface unmounting - emergency save if needed');

      // Emergency synchronous save attempt on unmount (navigation within app)
      // Use refs to access current state without adding dependencies
      const currentlyRecording = mediaRecorderRef.current?.state === 'recording' || mediaRecorderRef.current?.state === 'paused';
      if (currentlyRecording && audioChunks.current.length > 0) {
        try {
          console.log('Unmount: Emergency synchronous save of partial recording');

          // Create blob synchronously
          const partialBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
          audioBlobRef.current = partialBlob;

          // Try synchronous save (this might not work in all browsers, but worth attempting)
          saveDraftRecording({
            categoryId,
            subcategoryId,
            categoryName,
            subcategoryName,
            audioBlob: partialBlob,
            duration: Math.floor((Date.now() - (timerRef.current || 0)) / 1000),
            preSessionData,
            mimeType: partialBlob.type,
          }).then(id => {
            console.log('Unmount save completed:', id);
          }).catch(err => {
            console.error('Unmount save failed:', err);
          });
        } catch (error) {
          console.error('Failed to save on unmount:', error);
        }
      }

      // Clean up media recorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          console.debug('Cleanup: MediaRecorder already stopped', e);
        }
      }

      // Clean up audio stream
      if (streamRef.current) {
        try {
          streamRef.current.getTracks().forEach(track => track.stop());
        } catch (e) {
          console.debug('Cleanup: Error stopping tracks', e);
        }
      }

      // Revoke object URL to free memory (use ref to access current URL)
      const currentAudioURL = audioRef.current?.src;
      if (currentAudioURL && currentAudioURL.startsWith('blob:')) {
        try {
          URL.revokeObjectURL(currentAudioURL);
        } catch (e) {
          console.debug('Cleanup: Error revoking URL', e);
        }
      }

      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []); // Empty deps - only run on mount/unmount, use refs to access current state

  // If upload succeeded, show the success screen and stop rendering the recording UI
  if (uploadSuccess) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-2 border-green-200 dark:border-green-800 shadow-2xl">
          <CardContent className="pt-8 pb-8">
            <div className="text-center space-y-6">
              <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto shadow-lg">
                <Check className="w-10 h-10 text-green-600 dark:text-green-400" />
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-green-600 dark:text-green-400">
                  Upload Successful!
                </h3>
                <p className="text-foreground font-medium">Your recording has been submitted for processing.</p>
              </div>
              <div className="space-y-4">
                {jobId && (
                  <Button
                    onClick={() => router.navigate({ to: `/audio-recordings/${jobId}` })}
                    variant="outline"
                    className="w-full h-12 sm:h-14 text-sm sm:text-base font-semibold border-2 touch-manipulation"
                    style={{ touchAction: 'manipulation' }}
                  >
                    <Eye className="w-4 h-4 sm:w-5 sm:h-5 mr-2 sm:mr-3" />
                    View Details
                  </Button>
                )}
                <Button
                  onClick={onUploadComplete}
                  className="w-full h-12 sm:h-14 text-sm sm:text-base font-semibold bg-gradient-to-r from-zinc-700 to-zinc-800 hover:from-zinc-800 hover:to-zinc-700 shadow-lg hover:shadow-xl transition-all duration-200 touch-manipulation dark:from-zinc-200 dark:to-zinc-300 dark:hover:from-zinc-300 dark:hover:to-zinc-200 dark:text-zinc-800"
                  style={{ touchAction: 'manipulation' }}
                >
                  Record Another
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // clear any previous chunks
      audioChunks.current = [];
      setAudioURL(null);

      // Specify MediaRecorder options with timeslice for reliable chunk delivery
      const options: MediaRecorderOptions = {};
      
      // Use MP4/M4A (AAC) for all devices for maximum compatibility
      // Fallback to WebM only if MP4 not supported
      const mimeTypes = [
        'audio/mp4',                    // Primary: MP4 container with AAC
        'audio/mp4;codecs=mp4a.40.2',  // AAC-LC codec explicitly
        'audio/webm;codecs=opus',      // Fallback 1: WebM with Opus
        'audio/webm',                   // Fallback 2: WebM default codec
      ];
      
      for (const mimeType of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mimeType)) {
          options.mimeType = mimeType;
          console.debug('Using mimeType:', mimeType);
          break;
        }
      }

      const mr = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mr;
      console.debug('MediaRecorder created', { mr, options });

      mr.onstart = () => {
        setIsRecording(true);
        isRecordingRef.current = true; // Update ref for event listeners
        setIsPaused(false);
        setRecordingTime(0);
        // Removed toast - user can see recording started from UI changes
      };

      mr.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.current.push(event.data);
          console.debug(`[MediaRecorder] Data chunk received: ${event.data.size} bytes (total chunks: ${audioChunks.current.length})`);
        }
      };

      mr.onpause = () => {
        setIsPaused(true);
      };

      mr.onresume = () => {
        setIsPaused(false);
      };

      mr.onstop = () => {
        try {
          // Use the actual mimeType from the MediaRecorder, not hardcoded
          const mimeType = mr.mimeType || 'audio/webm';
          const audioBlob = new Blob(audioChunks.current, { type: mimeType });
          // Store the finalized blob in a ref so later code can access it even if state updates are delayed
          audioBlobRef.current = audioBlob;
          console.debug('Created audio blob', { 
            size: audioBlob.size, 
            type: audioBlob.type,
            chunks: audioChunks.current.length 
          });
          
          if (audioBlob.size === 0) {
            console.error('Audio blob is empty - no data recorded');
            recordingToasts.empty();
            return;
          }
          
          const url = URL.createObjectURL(audioBlob);
          setAudioURL(url);
        } catch (err) {
          console.error('Error creating audio blob:', err);
          toast.error('Could not create recording', {
            description: 'An error occurred while processing the audio'
          });
        }

        // DO NOT stop tracks here - let stopRecording() handle it
        // to avoid race conditions with MediaRecorder finalization
      };

      try {
        // Request data chunks every 1000ms so we have partial data available during recording
        // This enables auto-save on refresh/navigation even before stopping
        mr.start(1000);
        console.debug('MediaRecorder started with 1s timeslice', { state: mr.state });
      } catch (startErr) {
        console.error('MediaRecorder.start() failed', startErr);
        toast.error('Unable to start recording on this device/browser.', {
          description: 'Your browser may not support audio recording'
        });
        // stop tracks if start failed
        if (streamRef.current) {
          try { streamRef.current.getTracks().forEach(t => t.stop()); } catch (e) { /* ignore */ }
        }
        mediaRecorderRef.current = null;
        return;
      }
    } catch (error) {
      console.error("Error starting recording:", error);
      recordingToasts.microphoneError();
    }
  };

  const pauseRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'recording') {
      try {
        mr.pause();
        // onpause handler will update state
        // Removed toast - user can see recording paused from UI changes
      } catch (e) {
        console.warn('Pause failed', e);
      }
    }
  };

  const resumeRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'paused') {
      try {
        mr.resume();
        // onresume handler will update state
        // Removed toast - user can see recording resumed from UI changes
      } catch (e) {
        console.warn('Resume failed', e);
      }
    }
  };

  // Draft handling functions
  const saveDraft = async () => {
    if (!audioURL) {
      console.warn('No audio URL to save as draft');
      return;
    }

    try {
      const blob = await fetchAudioBlob(audioURL);
      
      if (blob.size === 0) {
        console.warn('Empty blob, skipping draft save');
        return;
      }

      const draftId = await saveDraftRecording({
        categoryId,
        subcategoryId,
        categoryName,
        subcategoryName,
        audioBlob: blob,
        duration: recordingTime,
        preSessionData,
        mimeType: blob.type,
      });

      setCurrentDraftId(draftId);
      recordingToasts.draftSaved();
      
      console.log('Draft saved:', draftId);
    } catch (error: any) {
      console.error('Failed to save draft:', error);
      
      // Show user-friendly error messages
      if (error.code === 'QUOTA_EXCEEDED') {
        storageToasts.full();
      } else if (error.code === 'SIZE_EXCEEDED') {
        toast.warning("Recording Too Large", {
          description: error.message,
        });
      } else {
        // Don't show toast for other errors (non-critical)
        console.warn('Draft save failed but continuing:', error.message);
      }
    }
  };

  const restoreDraft = async () => {
    if (!existingDraft) return;

    setIsRestoringDraft(true);
    try {
      // Create object URL from draft blob
      const url = URL.createObjectURL(existingDraft.audioBlob);
      setAudioURL(url);
      setRecordingTime(existingDraft.duration);
      setCurrentDraftId(existingDraft.id);
      
      // Clear the existing draft banner
      setExistingDraft(null);
      
      toast.success("Draft restored successfully", {
        description: "You can now continue with your recording"
      });
    } catch (error) {
      console.error('Failed to restore draft:', error);
      toast.error("Failed to restore draft", {
        description: "Please try again or contact support"
      });
    } finally {
      setIsRestoringDraft(false);
    }
  };

  const discardDraft = async () => {
    if (!existingDraft) return;

    try {
      await deleteDraftRecording(existingDraft.id);
      setExistingDraft(null);
      toast.success("Draft discarded", {
        description: "You can start a fresh recording"
      });
    } catch (error) {
      console.error('Failed to discard draft:', error);
      toast.error("Failed to discard draft");
    }
  };

  const downloadDraft = () => {
    if (!existingDraft) return;

    try {
      const url = URL.createObjectURL(existingDraft.audioBlob);
      const a = document.createElement('a');
      a.href = url;
      const fileName = `draft-recording-${new Date(existingDraft.timestamp).toISOString().replace(/[:.]/g, '-')}.${existingDraft.mimeType?.includes('mp4') ? 'm4a' : 'webm'}`;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      fileToasts.downloaded(fileName);
    } catch (error) {
      console.error('Failed to download draft:', error);
      fileToasts.downloadFailed("draft recording");
    }
  };

  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    console.debug('stopRecording invoked', { mrState: mr?.state, hasStream: !!streamRef.current });
    if (mr) {
      try {
        // If paused, resume first (some engines need this)
        if (mr.state === 'paused') {
          try { mr.resume(); console.debug('Resumed before stop'); } catch (e) { console.warn('resume before stop failed', e); }
        }

        if (mr.state === 'recording' || mr.state === 'paused') {
          try { mr.requestData(); } catch (e) { console.debug('requestData unsupported', e); }
          mr.stop();
          console.debug('mr.stop() called');
        } else if (mr.state === 'inactive') {
          console.debug('MediaRecorder already inactive');
        }
      } catch (e) {
        console.warn('MediaRecorder stop failed, falling back to track stop', e);
      }

      setIsRecording(false);
      isRecordingRef.current = false; // Update ref for event listeners
      setIsPaused(false);
      // Removed toast - user can see recording stopped from UI changes

      // Stop microphone tracks AFTER MediaRecorder has finished
      // Use a longer delay to ensure onstop handler completes and blob is finalized
      setTimeout(async () => {
        if (streamRef.current) {
          try {
            streamRef.current.getTracks().forEach(track => {
              console.debug('Stopping track:', track.label, track.readyState);
              track.stop();
            });
            console.debug('All tracks stopped');
          } catch (err) {
            console.warn('Error stopping tracks', err);
          }
        }
        // Clear refs after tracks are stopped
        mediaRecorderRef.current = null;
        streamRef.current = null;

        // Auto-save draft after stopping (after audio blob is created)
        // Wait a bit more for audioURL to be set
        setTimeout(async () => {
          // Prefer the finalized blob if available
          const blobToSave = audioBlobRef.current;
          if (blobToSave) {
            console.log('Auto-saving finalized recording');
            console.log('Auto-saving draft from blob (size=' + blobToSave.size + ')');
            await saveDraftFromBlob(blobToSave);
            // Don't clear the ref - keep it for unload handlers
          } else if (audioURL) {
            // fallback to the URL-based save
            console.log('Auto-saving draft from audioURL fallback');
            await saveDraft();
          } else {
            console.log('No audio blob or URL available to auto-save');
          }
        }, 100);
      }, 500); // Increased delay to 500ms for better reliability
    } else if (streamRef.current) {
      // Fallback: stop tracks if recorder not present
      try {
        streamRef.current.getTracks().forEach(track => track.stop());
        console.debug('Tracks stopped: recorder missing');
      } catch (err) {
        console.warn('Fallback stop tracks error', err);
      }
      setIsRecording(false);
      setIsPaused(false);
      // Removed toast - user can see recording stopped from UI changes
    }
  };
  const uploadRecording = async () => {
    if (!audioURL) return;
    setIsUploading(true);
    try {
      // Convert URL to File
      const blob = await fetchAudioBlob(audioURL);
      
      // Validate blob before proceeding
      if (blob.size === 0) {
        throw new Error('Recording is empty - no audio data available');
      }
      
      console.debug('Preparing to upload', { 
        blobSize: blob.size, 
        blobType: blob.type 
      });
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      // Determine file extension based on actual blob type
      const fileExtension = blob.type.includes('mp4') || blob.type.includes('m4a') ? 'm4a' :
                           blob.type.includes('webm') ? 'webm' : 
                           blob.type.includes('ogg') ? 'ogg' :
                           blob.type.includes('wav') ? 'wav' : 
                           blob.type.includes('mpeg') || blob.type.includes('mp3') ? 'mp3' :
                           'webm'; // fallback
      const fileName = `recording-${timestamp}.${fileExtension}`;
      const file = new File([blob], fileName, { type: blob.type || "audio/webm" });

      // Convert to WAV before upload (show progress)
      setIsConverting(true);
      setConversionProgress(0);
      setConversionStep("Starting conversion...");
      const wavFile = await convertToWavWithFFmpeg(file, {
        setConversionProgress,
        setConversionStep,
      });
      setIsConverting(false);
      setConversionStep("");

      const uploadResponse = await uploadFile(wavFile, categoryId, subcategoryId, preSessionData);
      if (uploadResponse?.job_id) {
        setJobId(uploadResponse.job_id);
      }
      setUploadSuccess(true);
      
      // Clear draft state from frontend so restoration banner doesn't show
      setExistingDraft(null);
      setCurrentDraftId(null);
      
      // Save uploaded recording as draft (with uploaded flag) for history, but don't show in restoration banner
      try {
        await saveDraftRecording({
          categoryId,
          subcategoryId,
          categoryName,
          subcategoryName,
          audioBlob: blob, // Save the original blob
          duration: recordingTime,
          preSessionData,
          uploaded: true,
          jobId: uploadResponse?.job_id,
        });
        console.log('Uploaded recording saved as draft with uploaded=true, jobId:', uploadResponse?.job_id);
      } catch (error) {
        console.warn('Failed to save uploaded recording as draft:', error);
      }
      
      uploadToasts.success();
    } catch (error) {
      console.error("Error uploading recording:", error);
      toast.error("Failed to upload recording", {
        description: "Please check your connection and try again"
      });
    } finally {
      setIsUploading(false);
      setIsConverting(false);
      setConversionStep("");
      setConversionProgress(0);
    }
  };

  // Reset recording state
  const resetRecording = () => {
    setAudioURL(null);
    setRecordingTime(0);
    setUploadSuccess(false);
    setJobId(null);
    audioChunks.current = [];
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
    }
  };

  // Save draft from a given Blob directly (more reliable than waiting for audioURL state)
  const saveDraftFromBlob = async (blob: Blob | null, showToast: boolean = true) => {
    if (!blob) {
      console.log('saveDraftFromBlob called with no blob');
      return;
    }

    // Debounce saves to prevent spam
    const now = Date.now();
    if (now - lastSaveTimeRef.current < 3000) {
      console.log('Debouncing save - too soon since last save');
      return;
    }
    lastSaveTimeRef.current = now;

    // Delete previous draft for this category/subcategory before saving new one
    if (currentDraftId) {
      try {
        await deleteDraftRecording(currentDraftId);
        console.log('Deleted previous draft: ' + currentDraftId);
        console.log('Deleted previous draft:', currentDraftId);
      } catch (error) {
        console.warn('Failed to delete previous draft:', error);
      }
    }

    try {
      console.log('Saving draft from blob (size=' + blob.size + ', type=' + blob.type + ')');
      const draftId = await saveDraftRecording({
        categoryId,
        subcategoryId,
        categoryName,
        subcategoryName,
        audioBlob: blob,
        duration: recordingTime,
        preSessionData,
        mimeType: blob.type,
      });
      setCurrentDraftId(draftId);
      
      // Only show toast if requested (not for periodic saves)
      if (showToast) {
        recordingToasts.draftSaved();
      }
      
      console.log('Draft saved: ' + draftId);
      console.log('Draft saved:', draftId);
    } catch (error: any) {
      console.error('Failed to save draft (from blob):', error);
      console.log('Draft save failed: ' + String(error?.message ?? error));
      if (error.code === 'QUOTA_EXCEEDED') {
        storageToasts.full();
      } else if (error.code === 'SIZE_EXCEEDED') {
        toast.warning('Recording Too Large', { description: error.message });
      }
    }
  };
  
  // Main render
  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="flex items-center space-x-3 sm:space-x-4 mb-6 sm:mb-8">
          <Button 
            variant="ghost" 
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground hover:bg-accent rounded-full h-10 w-10 sm:h-12 sm:w-12 p-0 touch-manipulation"
          >
            <ArrowLeft className="w-5 h-5 sm:w-6 sm:h-6" />
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-foreground truncate">
              Record Meeting
            </h1>
            <p className="text-sm text-muted-foreground font-medium truncate">{categoryName} • {subcategoryName}</p>
          </div>
        </div>

        {/* Draft Restoration Banner */}
        {existingDraft && !audioURL && (
          <DraftRestorationBanner
            draft={existingDraft}
            onRestore={restoreDraft}
            onDiscard={discardDraft}
            onDownload={downloadDraft}
            isRestoring={isRestoringDraft}
          />
        )}

        {/* Talking Points Display */}
        <TalkingPointsDisplay />

        {/* Recording Status */}
        <Card className="mb-6 shadow-xl border-2 bg-card backdrop-blur-sm">
          <CardContent className="pt-8 pb-8">
            <div className="text-center space-y-6">
              {/* Recording Button/Indicator */}
              <div className="relative">
                <Button
                  onClick={isRecording ? stopRecording : !audioURL ? startRecording : undefined}
                  disabled={audioURL !== null && !isRecording}
                  className={`w-32 h-32 sm:w-36 sm:h-36 rounded-full p-0 border-4 transition-all duration-300 transform hover:scale-105 active:scale-95 touch-manipulation relative z-10 ${
                    isRecording 
                      ? isPaused 
                        ? 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 border-orange-300' 
                        : 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-red-300'
                      : audioURL
                        ? 'bg-gradient-to-r from-gray-400 to-gray-500 border-gray-300 cursor-not-allowed'
                        : 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 border-green-300'
                  }`}
                  style={{ touchAction: 'manipulation' }}
                >
                  {isRecording ? (
                    <Square className="w-14 h-14 sm:w-16 sm:h-16 text-white drop-shadow-lg" />
                  ) : (
                    <Mic className="w-14 h-14 sm:w-16 sm:h-16 text-white drop-shadow-lg" />
                  )}
                </Button>
              </div>

              {/* Timer */}
              <div className="space-y-3">
                <div className="flex items-center justify-center space-x-3 bg-muted/50 rounded-full px-4 sm:px-6 py-2 sm:py-3 border-2 border-border">
                  <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-foreground" />
                  <span className="text-2xl sm:text-3xl font-mono font-bold text-foreground tracking-wider">
                    {formatTime(recordingTime)}
                  </span>
                </div>
                {/* Status text */}
                <div className="text-sm sm:text-base font-medium px-2">
                  {!isRecording && !audioURL && (
                    <span className="text-muted-foreground">Tap the microphone to start recording</span>
                  )}
                  {isRecording && !isPaused && (
                    <span className="text-red-600 font-semibold">Recording in progress...</span>
                  )}
                  {isRecording && isPaused && (
                    <span className="text-orange-600 font-semibold">Recording paused</span>
                  )}
                  {!isRecording && audioURL && (
                    <span className="text-green-600 font-semibold flex items-center justify-center gap-2">
                      <Check className="w-4 h-4 sm:w-5 sm:h-5" />
                      Recording complete
                    </span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Minimal Audio Level Indicator - Shown during recording */}
        {isRecording && (
          <div className="mb-4">
            <MinimalAudioIndicator 
              metrics={audioMetrics}
              className="max-w-md mx-auto"
            />
          </div>
        )}

        {/* Recording Controls */}
        {isRecording && (
          <div className="mb-6">
            <Button 
              onClick={isPaused ? resumeRecording : pauseRecording}
              variant="outline"
              className="w-full h-14 sm:h-16 text-base sm:text-lg font-semibold border-2 shadow-lg hover:shadow-xl transition-all duration-200 touch-manipulation"
              size="lg"
              style={{ touchAction: 'manipulation' }}
            >
              {isPaused ? (
                <>
                  <Play className="w-5 h-5 sm:w-6 sm:h-6 mr-3 text-green-600" />
                  Resume Recording
                </>
              ) : (
                <>
                  <Pause className="w-5 h-5 sm:w-6 sm:h-6 mr-3 text-orange-600" />
                  Pause Recording
                </>
              )}
            </Button>
          </div>
        )}

        {/* Playback and Upload */}
        {audioURL && !isRecording && (
          <div className="space-y-6">
            <Card className="shadow-lg border-2">
              <CardHeader>
                <CardTitle className="text-xl font-semibold bg-gradient-to-r from-zinc-800 to-zinc-600 dark:from-zinc-200 dark:to-zinc-400 bg-clip-text text-transparent">
                  Recording Playback
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border">
                  <span className="text-sm font-medium text-muted-foreground">Duration:</span>
                  <Badge variant="outline" className="text-sm font-semibold px-3 py-1">
                    {formatTime(recordingTime)}
                  </Badge>
                </div>
                {isIOS() ? (
                  <div className="p-4 bg-gradient-to-r from-orange-50 to-yellow-50 border-2 border-orange-200 rounded-lg text-orange-700 text-sm text-center font-medium">
                    Playback not supported on iOS
                  </div>
                ) : (
                  <div className="p-4 bg-muted/50 rounded-lg border-2">
                    <audio 
                      ref={audioRef}
                      src={audioURL} 
                      className="w-full"
                      controls
                    />
                  </div>
                )}
                {/* FFmpeg conversion progress */}
                {(isConverting || conversionProgress > 0) && (
                  <div className="p-4 bg-muted/50 rounded-lg border-2">
                    <div className="mb-2 text-sm font-medium text-foreground">{conversionStep}</div>
                    <Progress value={conversionProgress} className="h-2" />
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Button 
                    onClick={resetRecording}
                    variant="outline"
                    className="h-12 sm:h-14 text-sm sm:text-base font-semibold border-2 touch-manipulation"
                    style={{ touchAction: 'manipulation' }}
                  >
                    Record Again
                  </Button>
                  <Button 
                    onClick={uploadRecording}
                    disabled={isUploading || isConverting}
                    className="h-12 sm:h-14 text-sm sm:text-base font-semibold bg-gradient-to-r from-zinc-700 to-zinc-800 hover:from-zinc-800 hover:to-zinc-700 shadow-lg hover:shadow-xl transition-all duration-200 touch-manipulation dark:from-zinc-200 dark:to-zinc-300 dark:hover:from-zinc-300 dark:hover:to-zinc-200 dark:text-zinc-800"
                    style={{ touchAction: 'manipulation' }}
                  >
                    {isUploading || isConverting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 sm:h-5 sm:w-5 border-b-2 border-white mr-2 sm:mr-3"></div>
                        {isConverting ? "Converting..." : "Uploading..."}
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 sm:w-5 sm:h-5 mr-2 sm:mr-3" />
                        Submit Recording
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        <Alert className="mt-8 border-2 shadow-sm">
          <AlertCircle className="h-5 w-5 text-foreground" />
          <AlertDescription className="text-sm text-foreground font-medium">
            <strong className="text-foreground">Tips:</strong> Find a quiet space, speak clearly, and keep your device close to the speaker for best results.
          </AlertDescription>
        </Alert>

        {/* Upload existing recording footnote */}
        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Have an existing recording?{" "}
            <button
              onClick={() => router.navigate({ to: "/audio-upload" })}
              className="text-foreground underline hover:text-muted-foreground font-medium transition-colors"
            >
              Upload it here
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
