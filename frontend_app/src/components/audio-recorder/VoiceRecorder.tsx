import { useRef, useState } from "react";
import { Mic, Square } from "lucide-react"; // Make sure you have lucide-react or use any icon library

interface VoiceRecorderProps {
  onRecordingComplete?: (file: File) => void;
}

export function VoiceRecorder({ onRecordingComplete }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);

    mediaRecorderRef.current.ondataavailable = (event) => {
      audioChunks.current.push(event.data);
    };

    mediaRecorderRef.current.onstop = () => {
      const audioBlob = new Blob(audioChunks.current, { type: "audio/webm" });
      const url = URL.createObjectURL(audioBlob);
      setAudioURL(url);
      audioChunks.current = [];

      const file = new File([audioBlob], "recording.webm", { type: "audio/webm" });
      if (onRecordingComplete) {
        onRecordingComplete(file);
      }
    };

    mediaRecorderRef.current.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  return (
    <div className="space-y-4">
      <div className="pt-4 pb-2 text-center">
        {!isRecording ? (
          <button
            onClick={startRecording}
            className="w-16 h-16 flex items-center justify-center rounded-full bg-green-500 text-white shadow-lg hover:bg-green-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-green-400"
            aria-label="Start Recording"
          >
            <Mic className="w-8 h-8" />
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="w-16 h-16 flex items-center justify-center rounded-full bg-red-500 text-white shadow-lg animate-pulse hover:bg-red-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-red-400"
            aria-label="Stop Recording"
          >
            <Square className="w-8 h-8" />
          </button>
        )}
      </div>

      {audioURL && (
        <audio controls src={audioURL} className="mt-4 w-full" />
      )}
    </div>
  );
}