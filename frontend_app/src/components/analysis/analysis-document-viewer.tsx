import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { 
  Save, 
  Edit3, 
  Download, 
  FileText, 
  AlertTriangle,
  Loader2,
  CheckCircle 
} from 'lucide-react';
import { toast } from 'sonner';

interface AnalysisSection {
  id: string;
  title: string;
  content: string[];
  type: 'heading' | 'paragraph' | 'list';
}

interface AnalysisDocumentViewerProps {
  analysisText: string;
  analysisFilePath?: string;
  jobId: string;
  isEditable: boolean; // true if DOCX, false if PDF
  onSave?: (updatedContent: string) => Promise<void>;
  onDownload?: (filePath: string, fileName: string) => void;
}

export function AnalysisDocumentViewer({
  analysisText,
  analysisFilePath,
  jobId,
  isEditable,
  onSave,
  onDownload
}: AnalysisDocumentViewerProps) {
  const [sections, setSections] = useState<AnalysisSection[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editedSections, setEditedSections] = useState<AnalysisSection[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);



  // Check if we have actual analysis text or just a placeholder
  const hasRealAnalysisText = analysisText && 
    analysisText.trim() !== '' && 
    analysisText !== 'Loading analysis content...' &&
    analysisText.length > 20; // Ensure it's not just a short placeholder

  // Helper function to extract filename from URL for display
  const getDisplayFilename = useCallback((filePath?: string): string => {
    if (!filePath) return 'Unknown file';
    
    try {
      const urlObj = new URL(filePath);
      const pathname = urlObj.pathname;
      const filename = pathname.split('/').pop() || 'analysis.docx';
      return filename;
    } catch {
      // Fallback for non-URL paths
      const filename = filePath.split('/').pop() || filePath.split('\\').pop() || 'analysis.docx';
      return filename;
    }
  }, []);

  // Parse analysis text into structured sections
  const parseAnalysisText = useCallback((text: string): AnalysisSection[] => {
    const parsed: AnalysisSection[] = [];
    const sections = text.split('\n\n').filter(section => section.trim());

    sections.forEach((section, index) => {
      const lines = section.split('\n').filter(line => line.trim());
      if (lines.length === 0) return;

      const firstLine = lines[0].trim();
      const restLines = lines.slice(1).filter(line => line.trim());

      // Determine if first line is a heading - improved detection
      const isHeading = 
        // Markdown-style headings (###, ##, #)
        /^#{1,6}\s/.test(firstLine) ||
        // Bold markdown (**text**)
        /^\*\*.*\*\*$/.test(firstLine) ||
        // Section numbers (1., 2., etc.)
        /^\d+\.\s*\*\*.*\*\*$/.test(firstLine) ||
        // Ends with colon
        firstLine.endsWith(':') ||
        // Short lines that look like titles (less than 100 chars, title case)
        (firstLine.length < 100 && /^[A-Z]/.test(firstLine) && !firstLine.includes('.')) ||
        // All caps
        /^[A-Z][A-Z\s]*:?$/.test(firstLine);

      if (isHeading) {
        // Preserve original heading text with markdown formatting
        let headingTitle = firstLine
          .replace(/^#{1,6}\s*/, '') // Remove ### but keep other formatting
          .replace(/^\d+\.\s*/, '') // Remove 1. 
          .replace(':$', '') // Remove trailing colon
          .trim();

        // Add heading section
        parsed.push({
          id: `section-${index}-heading`,
          title: headingTitle,
          content: [],
          type: 'heading'
        });

        // Add content section if there are remaining lines
        if (restLines.length > 0) {
          // Detect if content is a list
          const isList = restLines.some(line => 
            line.startsWith('•') || 
            line.startsWith('-') || 
            line.startsWith('*') ||
            /^\d+\./.test(line) ||
            line.startsWith('  -') || // Indented lists
            line.startsWith('    -') // More indented lists
          );

          parsed.push({
            id: `section-${index}-content`,
            title: '',
            content: restLines,
            type: isList ? 'list' : 'paragraph'
          });
        }
      } else {
        // Regular content section
        const isList = lines.some(line => 
          line.startsWith('•') || 
          line.startsWith('-') || 
          line.startsWith('*') ||
          /^\d+\./.test(line) ||
          line.startsWith('  -') || // Indented lists
          line.startsWith('    -') // More indented lists
        );

        parsed.push({
          id: `section-${index}`,
          title: '',
          content: lines,
          type: isList ? 'list' : 'paragraph'
        });
      }
    });

    return parsed;
  }, []);

  // Initialize sections when analysisText changes
  useEffect(() => {
    // Only parse if we have real analysis text
    if (hasRealAnalysisText) {
      const parsedSections = parseAnalysisText(analysisText);
      setSections(parsedSections);
      setEditedSections(parsedSections);
    } else if (analysisFilePath) {
      // If we have a file path but no text, show a file-based view
      const fileViewSection: AnalysisSection = {
        id: 'file-view',
        title: 'Analysis Document',
        content: [`This analysis is stored as a ${getFileType(analysisFilePath).toUpperCase()} file.`],
        type: 'paragraph'
      };
      setSections([fileViewSection]);
      setEditedSections([fileViewSection]);
    } else {
      // No content at all
      setSections([]);
      setEditedSections([]);
    }
  }, [analysisText, parseAnalysisText, hasRealAnalysisText, analysisFilePath]);

  // Determine file type from path (handles URLs with query parameters)
  const getFileType = useCallback((filePath?: string): 'docx' | 'pdf' | 'unknown' => {
    if (!filePath) return 'unknown';
    
    try {
      const urlObj = new URL(filePath);
      const pathname = urlObj.pathname;
      const lastDot = pathname.lastIndexOf('.');
      const extension = lastDot !== -1 ? pathname.substring(lastDot + 1).toLowerCase() : '';
      return extension === 'docx' ? 'docx' : extension === 'pdf' ? 'pdf' : 'unknown';
    } catch {
      // Fallback for non-URL paths
      const lastDot = filePath.lastIndexOf('.');
      const questionMark = filePath.indexOf('?');
      const endPos = questionMark !== -1 ? questionMark : filePath.length;
      const extension = lastDot !== -1 && lastDot < endPos ? filePath.substring(lastDot + 1, endPos).toLowerCase() : '';
      return extension === 'docx' ? 'docx' : extension === 'pdf' ? 'pdf' : 'unknown';
    }
  }, []);

  const fileType = getFileType(analysisFilePath);



  // Handle editing a section
  const handleEditSection = (sectionId: string, newContent: string[]) => {
    setEditedSections(prev => 
      prev.map(section => 
        section.id === sectionId 
          ? { ...section, content: newContent }
          : section
      )
    );
  };

  // Handle editing a section title
  const handleEditSectionTitle = (sectionId: string, newTitle: string) => {
    setEditedSections(prev => 
      prev.map(section => 
        section.id === sectionId 
          ? { ...section, title: newTitle }
          : section
      )
    );
  };

  // Convert sections back to text
  const sectionsToText = (sectionsData: AnalysisSection[]): string => {
    return sectionsData.map(section => {
      if (section.type === 'heading') {
        // Preserve the original heading format with markdown
        return section.title + ':';
      }
      
      const titleLine = section.title ? section.title + ':' : '';
      
      if (section.type === 'list') {
        // Preserve list formatting with bullet points
        const listItems = section.content.map(item => {
          // If item already has a bullet, keep it; otherwise add one
          const cleanItem = item.replace(/^[•\-\*\d+\.]\s*/, '').trim();
          return cleanItem ? `• ${cleanItem}` : '';
        }).filter(item => item);
        
        return titleLine ? `${titleLine}\n${listItems.join('\n')}` : listItems.join('\n');
      } else {
        // Regular paragraphs - preserve original formatting
        const contentLines = section.content.join('\n');
        return titleLine ? `${titleLine}\n${contentLines}` : contentLines;
      }
    }).filter(section => section.trim()).join('\n\n');
  };

  // Handle save
  const handleSave = async () => {
    if (!onSave) return;

    setIsSaving(true);
    try {
      const updatedText = sectionsToText(editedSections);
      await onSave(updatedText);
      setSections(editedSections);
      setIsEditing(false);
      setShowSaveDialog(false);
      toast.success('Analysis document updated successfully');
    } catch (error) {
      console.error('Failed to save:', error);
      toast.error('Failed to save changes. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  // Handle cancel editing
  const handleCancelEdit = () => {
    setEditedSections(sections);
    setIsEditing(false);
  };

  // Render section content
  const renderSectionContent = (section: AnalysisSection, isEditMode: boolean = false) => {
    const sectionData = isEditMode ? editedSections.find(s => s.id === section.id) || section : section;

    if (section.type === 'heading') {
      return (
        <div className="mb-4">
          {isEditMode ? (
            <input
              type="text"
              value={sectionData.title}
              onChange={(e) => handleEditSectionTitle(section.id, e.target.value)}
              className="text-xl font-semibold text-foreground bg-transparent border-b border-border focus:border-primary outline-none w-full pb-1"
            />
          ) : (
            <h3 className="text-xl font-semibold text-foreground mb-2">
              <span dangerouslySetInnerHTML={{ 
                __html: renderMarkdownText(sectionData.title) 
              }} />
            </h3>
          )}
        </div>
      );
    }

    if (section.type === 'list') {
      return (
        <div className="space-y-2">
          {isEditMode ? (
            <div className="space-y-2">
              {sectionData.content.map((item, index) => (
                <div key={index} className="flex items-start gap-2">
                  <span className="text-muted-foreground mt-1">•</span>
                  <input
                    type="text"
                    value={item.replace(/^[•\-\*\d+\.]\s*/, '')}
                    onChange={(e) => {
                      const newContent = [...sectionData.content];
                      newContent[index] = `• ${e.target.value}`;
                      handleEditSection(section.id, newContent);
                    }}
                    className="flex-1 bg-transparent border-b border-border focus:border-primary outline-none pb-1 text-sm"
                  />
                </div>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const newContent = [...sectionData.content, '• '];
                  handleEditSection(section.id, newContent);
                }}
                className="text-xs text-muted-foreground"
              >
                + Add item
              </Button>
            </div>
          ) : (
            <ul className="space-y-1">
              {sectionData.content.map((item, index) => {
                // Process markdown formatting in list items
                const cleanItem = item.replace(/^[•\-\*\d+\.]\s*/, '').trim();
                
                return (
                  <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="text-primary mt-1">•</span>
                    <span dangerouslySetInnerHTML={{ 
                      __html: renderMarkdownText(cleanItem) 
                    }} />
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      );
    }

    // Regular paragraph
    return (
      <div className="space-y-2">
        {isEditMode ? (
          <div className="space-y-2">
            {sectionData.content.map((paragraph, index) => (
              <textarea
                key={index}
                value={paragraph}
                onChange={(e) => {
                  const newContent = [...sectionData.content];
                  newContent[index] = e.target.value;
                  handleEditSection(section.id, newContent);
                }}
                className="w-full bg-transparent border border-border rounded-md p-2 focus:border-primary outline-none text-sm resize-none"
                rows={Math.max(2, Math.ceil(paragraph.length / 80))}
              />
            ))}
          </div>
        ) : (
          sectionData.content.map((paragraph, index) => (
            <p key={index} className="text-sm text-muted-foreground leading-relaxed">
              <span dangerouslySetInnerHTML={{ 
                __html: renderMarkdownText(paragraph) 
              }} />
            </p>
          ))
        )}
      </div>
    );
  };

  // Render markdown text to HTML
  const renderMarkdownText = useCallback((text: string): string => {
    // First escape HTML to prevent XSS
    let processed = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;');
    
    // Then process markdown (order matters - bold before italic)
    processed = processed
      // Bold text (**text** or __text__)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      // Italic text (*text* or _text_) - process remaining single * and _
      .replace(/\*([^*]+?)\*/g, '<em>$1</em>')
      .replace(/_([^_]+?)_/g, '<em>$1</em>')
      // Line breaks
      .replace(/\n/g, '<br />');
    
    return processed;
  }, []);

  return (
    <div className="space-y-4">
      {/* Header with file type indicator and actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <span className="font-medium">Analysis Document</span>
          <Badge variant={fileType === 'docx' ? 'default' : 'secondary'} className="text-xs">
            {fileType.toUpperCase()}
          </Badge>
          {!isEditable && (
            <Badge variant="outline" className="text-xs">
              Read-only
            </Badge>
          )}
          {isEditable && (
            <Badge variant="default" className="text-xs bg-green-500">
              Editable
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Edit button - only show for DOCX files */}
          {isEditable && !isEditing && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // If we don't have real analysis text, create a starter template
                if (!hasRealAnalysisText) {
                  const starterSection: AnalysisSection = {
                    id: 'starter-section',
                    title: 'Analysis Report',
                    content: ['Start writing your analysis here...'],
                    type: 'paragraph'
                  };
                  setSections([starterSection]);
                  setEditedSections([starterSection]);
                }
                setIsEditing(true);
              }}
              className="transition-all duration-200 hover:scale-105"
            >
              <Edit3 className="mr-2 h-4 w-4" />
              {hasRealAnalysisText ? 'Edit' : 'Create Analysis'}
            </Button>
          )}

          {/* Download button */}
          {analysisFilePath && onDownload && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDownload(analysisFilePath, `Analysis_${jobId}.${fileType}`)}
              className="transition-all duration-200 hover:scale-105"
            >
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
          )}
        </div>
      </div>

      {/* Main document viewer */}
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-6">
          <div className="max-h-[600px] lg:max-h-[700px] xl:max-h-[800px] overflow-y-auto space-y-6 pr-2">
            {/* Regular sections - show when we have real content or in edit mode */}
            {(hasRealAnalysisText || isEditing) && sections.filter(s => s.id !== 'file-view').map((section, index) => (
              <div 
                key={section.id} 
                className="animate-in fade-in duration-500" 
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {renderSectionContent(section, isEditing)}
                {index < sections.filter(s => s.id !== 'file-view').length - 1 && <Separator className="my-6" />}
              </div>
            ))}

            {/* Empty state - when no content and not editing */}
            {sections.length === 0 && !isEditing && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <div className="text-center space-y-2">
                  <p className="text-muted-foreground">No analysis content available</p>
                  {analysisFilePath && (
                    <p className="text-sm text-muted-foreground">
                      The analysis is stored as a file. Use the download button to access it.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Special case: file exists but no content loaded */}
            {sections.length === 1 && sections[0].id === 'file-view' && !isEditing && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="rounded-full bg-blue-50 p-4">
                  <FileText className="h-8 w-8 text-blue-600" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="font-medium">Analysis Document Available</h3>
                  <p className="text-sm text-muted-foreground">
                    Your analysis is stored as a {fileType.toUpperCase()} file.
                  </p>
                  <div className="flex items-center gap-2 mt-4">
                    {analysisFilePath && onDownload && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onDownload(analysisFilePath, `Analysis_${jobId}.${fileType}`)}
                        className="transition-all duration-200 hover:scale-105"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download {fileType.toUpperCase()}
                      </Button>
                    )}
                    {isEditable && (
                      <p className="text-xs text-muted-foreground">
                        Download to edit, or create a new analysis with the Edit button above.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Edit mode controls */}
          {isEditing && (
            <div className="mt-6 pt-6 border-t border-border/50 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                onClick={() => setShowSaveDialog(true)}
                disabled={isSaving}
                className="transition-all duration-200 hover:scale-105"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Save confirmation dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Confirm Changes
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto space-y-4">
            <p className="text-sm text-muted-foreground">
              Are you sure you want to save these changes? This will update the analysis document file and cannot be undone.
            </p>
            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">File to be updated:</p>
              <div className="space-y-2">
                <p className="text-sm font-medium">{getDisplayFilename(analysisFilePath)}</p>
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    Show full path
                  </summary>
                  <div className="mt-2 text-xs font-mono break-all max-h-20 overflow-y-auto p-2 bg-muted/30 rounded border">
                    {analysisFilePath}
                  </div>
                </details>
              </div>
            </div>
          </div>
          <DialogFooter className="flex-shrink-0 mt-4">
            <Button
              variant="outline"
              onClick={() => setShowSaveDialog(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving}
              className="transition-all duration-200 hover:scale-105"
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
