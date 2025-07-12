import React, { useState } from "react";
import { TrendingUp, FileText, Activity, Clock, Target, Download, MessageSquare, Lightbulb } from "lucide-react";
import { usePromptManagement } from "./prompt-management-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";

interface PromptAnalyticsDashboardProps {
  selectedCategory: any;
  selectedSubcategory: any;
}

export function PromptAnalyticsDashboard({ selectedCategory, selectedSubcategory }: PromptAnalyticsDashboardProps) {
  const { subcategories } = usePromptManagement();
  const [selectedTimeframe, setSelectedTimeframe] = useState<'7d' | '30d' | '90d'>('30d');
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsPageSize] = useState(10);
  const [jobsTotal, setJobsTotal] = useState(0);

  // Check admin permission on mount
  React.useEffect(() => {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    setIsAdmin(user?.permission === "admin");
  }, []);

  // Fetch paginated jobs for dashboard (all jobs, category, or prompt)
  const fetchJobs = React.useCallback((_page: number, pageSize: number, promptId?: string) => {
    setLoadingJobs(true);
    const token = localStorage.getItem("token");
    // Backend endpoint: /api/analytics/jobs?limit=pageSize&prompt_id=promptId
    let url = `/api/analytics/jobs?limit=${pageSize}`;
    if (promptId) url += `&prompt_id=${promptId}`;
    // For real backend, use fetch with token
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        setRecentJobs(data.jobs || []);
        setJobsTotal(data.total || 0);
      })
      .catch(() => {
        setRecentJobs([]);
        setJobsTotal(0);
      })
      .finally(() => setLoadingJobs(false));
  }, []);

  // Fetch jobs when page/category/prompt changes
  React.useEffect(() => {
    if (!selectedCategory && !selectedSubcategory && isAdmin) {
      fetchJobs(jobsPage, jobsPageSize);
    } else if (selectedCategory && !selectedSubcategory) {
      // Category jobs: filter by category id if backend supports
      fetchJobs(jobsPage, jobsPageSize);
    } else if (selectedSubcategory) {
      // Prompt jobs: filter by prompt id
      const promptEntries = Object.entries(selectedSubcategory.prompts || {});
      const promptId = promptEntries.length > 0 ? promptEntries[0][0] : null;
      if (promptId) fetchJobs(jobsPage, jobsPageSize, promptId);
    }
  }, [selectedCategory, selectedSubcategory, isAdmin, jobsPage, jobsPageSize, fetchJobs]);

  // Pagination controls
  const totalPages = Math.ceil(jobsTotal / jobsPageSize);
  const handlePrevPage = () => setJobsPage((p) => Math.max(1, p - 1));
  const handleNextPage = () => setJobsPage((p) => Math.min(totalPages, p + 1));

  // Mock data generation for analytics
  const generateMockJobs = (promptId: string, count: number) => {
    const statuses = ['completed', 'in-progress', 'failed', 'pending'];
    const users = ['Alice Johnson', 'Bob Smith', 'Carol Davis', 'David Wilson', 'Eva Martinez'];
    const projects = ['Project Alpha', 'Project Beta', 'Project Gamma', 'Project Delta'];
    
    return Array.from({ length: count }, (_, i) => ({
      id: `job-${promptId}-${i + 1}`,
      name: `Analysis Job ${i + 1}`,
      status: statuses[Math.floor(Math.random() * statuses.length)],
      user: users[Math.floor(Math.random() * users.length)],
      project: projects[Math.floor(Math.random() * projects.length)],
      duration: `${Math.floor(Math.random() * 120) + 30}s`,
      accuracy: Math.floor(Math.random() * 30) + 70,
      createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toLocaleDateString(),
      tokensUsed: Math.floor(Math.random() * 5000) + 1000,
    }));
  };

  const generateMockMetrics = (baseUsage: number) => {
    const timeframes = {
      '7d': Array.from({ length: 7 }, () => Math.floor(baseUsage * (0.8 + Math.random() * 0.4))),
      '30d': Array.from({ length: 30 }, () => Math.floor(baseUsage * (0.7 + Math.random() * 0.6))),
      '90d': Array.from({ length: 90 }, () => Math.floor(baseUsage * (0.6 + Math.random() * 0.8)))
    };
    
    return {
      usage: timeframes[selectedTimeframe],
      avgResponseTime: Math.floor(Math.random() * 3000) + 1000,
      successRate: Math.floor(Math.random() * 20) + 80,
      peakUsageHour: Math.floor(Math.random() * 24),
      topUser: ['Alice Johnson', 'Bob Smith', 'Carol Davis'][Math.floor(Math.random() * 3)],
      totalTokens: Math.floor(Math.random() * 100000) + 50000,
    };
  };

  // Calculate prompt-related analytics data
  const totalPrompts = subcategories.reduce((acc, sub) => acc + Object.keys(sub.prompts || {}).length, 0);
  const totalUsage = subcategories.reduce((acc) => acc + Math.floor(Math.random() * 100) + 20, 0);

  // If nothing is selected, show overall analytics
  if (!selectedCategory && !selectedSubcategory) {
    return (
      <PermissionGuard requiredCapability={Capability.CAN_VIEW_ALL_JOBS} fallback={<div className="p-6 text-lg font-semibold text-red-600">Admin access required to view recent jobs.</div>}>
        <div className="space-y-6 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-blue-600 dark:text-blue-400">Prompt Analytics</h2>
              <p className="text-gray-600 dark:text-gray-400">Prompt-related performance overview</p>
            </div>
            <div className="flex gap-2">
              {['7d', '30d', '90d'].map((period) => (
                <Button
                  key={period}
                  variant={selectedTimeframe === period ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedTimeframe(period as any)}
                >
                  {period}
                </Button>
              ))}
            </div>
          </div>

          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="jobs">Recent Jobs</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-600" />
                      Total Prompts
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{totalPrompts}</div>
                    <p className="text-xs text-green-600 flex items-center gap-1 mt-1">
                      <TrendingUp className="h-3 w-3" />
                      +12% from last month
                    </p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Activity className="h-4 w-4 text-green-600" />
                      Total Usage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{totalUsage.toLocaleString()}</div>
                    <p className="text-xs text-green-600 flex items-center gap-1 mt-1">
                      <TrendingUp className="h-3 w-3" />
                      +8% from last month
                    </p>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="jobs" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Jobs</CardTitle>
                </CardHeader>
                <CardContent>
                  {loadingJobs ? (
                    <div className="text-gray-500">Loading jobs...</div>
                  ) : (
                    <div className="space-y-3">
                      {recentJobs.map((job) => (
                        <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="space-y-1">
                            <div className="font-medium">{job.name}</div>
                            <div className="text-sm text-gray-600">
                              {job.user} • {job.project} • {job.createdAt}
                            </div>
                            <div className="text-xs text-blue-600">Prompt: Unknown Prompt</div>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge 
                              variant={job.status === 'completed' ? 'default' : 
                                      job.status === 'failed' ? 'destructive' : 'secondary'}
                            >
                              {job.status}
                            </Badge>
                            <div className="text-sm text-gray-500">{job.duration}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </PermissionGuard>
    );
  }

  // If a category is selected, show analytics for that category
  if (selectedCategory && !selectedSubcategory) {
    const categorySubcategories = subcategories.filter(sub => sub.category_id === selectedCategory.id);
    const categoryPrompts = categorySubcategories.reduce((acc, sub) => acc + Object.keys(sub.prompts || {}).length, 0);
    const categoryUsage = categorySubcategories.reduce((acc) => acc + Math.floor(Math.random() * 50) + 10, 0);
    const categoryMetrics = generateMockMetrics(categoryUsage);
    const categoryJobs = generateMockJobs(selectedCategory.id, 8);
    
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-blue-600 dark:text-blue-400">{selectedCategory.name} Analytics</h2>
            <p className="text-gray-600 dark:text-gray-400">Category performance overview</p>
          </div>
          <div className="flex gap-2">
            {['7d', '30d', '90d'].map((period) => (
              <Button
                key={period}
                variant={selectedTimeframe === period ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedTimeframe(period as any)}
              >
                {period}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FileText className="h-4 w-4 text-blue-600" />
                Prompts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{categoryPrompts}</div>
              <p className="text-xs text-gray-600 mt-1">
                Across {categorySubcategories.length} subcategories
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4 text-green-600" />
                Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{categoryUsage}</div>
              <p className="text-xs text-green-600 flex items-center gap-1 mt-1">
                <TrendingUp className="h-3 w-3" />
                +{Math.floor(Math.random() * 20) + 5}% this period
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Target className="h-4 w-4 text-purple-600" />
                Success Rate
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{categoryMetrics.successRate}%</div>
              <Progress value={categoryMetrics.successRate} className="mt-2" />
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Subcategory Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {categorySubcategories.map((sub) => {
                  const subUsage = Math.floor(Math.random() * 30) + 5;
                  return (
                    <div key={sub.id} className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{sub.name}</div>
                        <div className="text-sm text-gray-600">
                          {Object.keys(sub.prompts || {}).length} prompts
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">{subUsage}</div>
                        <div className="text-sm text-gray-600">uses</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Category Jobs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {categoryJobs.slice(0, 5).map((job) => (
                  <div key={job.id} className="flex items-center justify-between p-2 border rounded">
                    <div className="space-y-1">
                      <div className="font-medium text-sm">{job.name}</div>
                      <div className="text-xs text-gray-600">{job.user} • {job.createdAt}</div>
                    </div>
                    <Badge 
                      variant={job.status === 'completed' ? 'default' : 
                              job.status === 'failed' ? 'destructive' : 'secondary'}
                      className="text-xs"
                    >
                      {job.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-blue-500" />
              {selectedCategory.name} Category Talking Points
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Performance Summary</h4>
                <div className="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <Activity className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-blue-900 dark:text-blue-100">
                      Category Overview
                    </div>
                    <div className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                      {selectedCategory.name} contains {categoryPrompts} prompts across {categorySubcategories.length} subcategories with {categoryUsage} total executions.
                    </div>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <Target className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-green-900 dark:text-green-100">
                      Success Metrics
                    </div>
                    <div className="text-sm text-green-700 dark:text-green-300 mt-1">
                      Maintaining {categoryMetrics.successRate}% success rate with average response time of {categoryMetrics.avgResponseTime}ms.
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Key Recommendations</h4>
                <div className="flex items-start gap-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <Lightbulb className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-yellow-900 dark:text-yellow-100">
                      Optimize High-Usage Prompts
                    </div>
                    <div className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                      Consider auto-scaling and caching for most-used prompts.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
                  <Target className="h-5 w-5 text-indigo-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-indigo-900 dark:text-indigo-100">
                      Expand High-Performing Prompts
                    </div>
                    <div className="text-sm text-indigo-700 dark:text-indigo-300 mt-1">
                      Develop more prompts in categories with highest success rates.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // If a subcategory is selected, show detailed analytics for that subcategory
  if (selectedSubcategory) {
    const promptEntries = Object.entries(selectedSubcategory.prompts || {});
    const promptId = promptEntries.length > 0 ? promptEntries[0][0] : null;
    const promptContent = promptEntries.length > 0 ? String(promptEntries[0][1]) : null;
    // Simulate job data for the selected prompt
    const jobs = promptId ? generateMockJobs(promptId, 15) : [];
    const totalUses = jobs.length;
    const recentUses = jobs.slice(0, 5);
    const usage = Math.floor(Math.random() * 80) + 20;
    const metrics = generateMockMetrics(usage);
    
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-blue-600 dark:text-blue-400">{selectedSubcategory.name}</h2>
            <p className="text-gray-600 dark:text-gray-400">Prompt analytics</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
            {['7d', '30d', '90d'].map((period) => (
              <Button
                key={period}
                variant={selectedTimeframe === period ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedTimeframe(period as any)}
              >
                {period}
              </Button>
            ))}
          </div>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="recent">Recent Use</TabsTrigger>
            <TabsTrigger value="jobs">All Jobs</TabsTrigger>
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4 text-blue-600" />
                    Prompt Content
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-gray-700 dark:text-gray-200">
                    {promptContent ? promptContent.substring(0, 120) + (promptContent.length > 120 ? '...' : '') : 'No content'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Activity className="h-4 w-4 text-green-600" />
                    Total Uses
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{totalUses}</div>
                  <p className="text-xs text-green-600 mt-1">Across all jobs</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Clock className="h-4 w-4 text-orange-600" />
                    Avg Duration
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{Math.floor(metrics.avgResponseTime / 1000)}s</div>
                  <p className="text-xs text-gray-600 mt-1">Per job execution</p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="recent" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent Use</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentUses.length === 0 ? (
                    <div className="text-gray-500">No recent jobs for this prompt.</div>
                  ) : (
                    recentUses.map((job) => (
                      <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="space-y-1">
                          <div className="font-medium">{job.name}</div>
                          <div className="text-sm text-gray-600">
                            {job.user} • {job.project} • {job.createdAt}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge 
                            variant={job.status === 'completed' ? 'default' : 
                                    job.status === 'failed' ? 'destructive' : 'secondary'}
                          >
                            {job.status}
                          </Badge>
                          <div className="text-sm text-gray-500">{job.duration}</div>
                        </div>
                      </div>
                    ))
                    )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="jobs" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>All Jobs ({recentJobs.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingJobs ? (
                  <div className="text-gray-500">Loading jobs...</div>
                ) : (
                  <div className="space-y-3">
                    {recentJobs.map((job) => (
                      <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="space-y-1">
                          <div className="font-medium">{job.name}</div>
                          <div className="text-sm text-gray-600">
                            {job.user} • {job.project} • {job.createdAt}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge 
                            variant={job.status === 'completed' ? 'default' : 
                                    job.status === 'failed' ? 'destructive' : 'secondary'}
                          >
                            {job.status}
                          </Badge>
                          <div className="text-sm text-gray-500">{job.duration}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex justify-between items-center mt-4">
                  <Button size="sm" variant="outline" onClick={handlePrevPage} disabled={jobsPage === 1}>Previous</Button>
                  <span className="text-sm">Page {jobsPage} of {totalPages}</span>
                  <Button size="sm" variant="outline" onClick={handleNextPage} disabled={jobsPage === totalPages}>Next</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="metrics" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Prompt Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <div className="text-gray-600">Success Rate</div>
                    <div className="font-semibold text-green-600">{metrics.successRate}%</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Avg Duration</div>
                    <div className="font-semibold">{Math.floor(metrics.avgResponseTime / 1000)}s</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Peak Usage Hour</div>
                    <div className="font-semibold">{metrics.peakUsageHour}:00</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Total Tokens Used</div>
                    <div className="font-semibold">{metrics.totalTokens.toLocaleString()}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  // fallback
  return null;
}