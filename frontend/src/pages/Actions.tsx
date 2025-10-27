import { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { processFile, FileAction, fetchWorksheets } from '../services/api';
import { toast } from 'react-hot-toast';
import { ArrowUpTrayIcon, XCircleIcon, CheckCircleIcon, CubeTransparentIcon, DocumentArrowUpIcon, DocumentMinusIcon, DocumentCheckIcon, CreditCardIcon, ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline';
import { NavLink } from 'react-router-dom';
import { useActionProgress } from '../hooks/useActionProgress';

interface ActionsProps {
  sheetUrl: string;
}

const actionButtons = [
  { id: 'upload_orders', label: 'Upload Orders', icon: DocumentArrowUpIcon },
  { id: 'cancel_orders', label: 'Cancel Orders', icon: DocumentMinusIcon },
  { id: 'upload_trackings', label: 'Track Orders', icon: ClipboardDocumentCheckIcon },
  { id: 'mark_received', label: 'Mark Received', icon: DocumentCheckIcon },
  { id: 'reconcile_charges', label: 'Reconcile Charges', icon: CreditCardIcon },
] as const;

export default function Actions({ sheetUrl }: ActionsProps) {
  const [file, setFile] = useState<File | null>(null);
  const [action, setAction] = useState<FileAction>('upload_orders');
  const [selectedWorksheet, setSelectedWorksheet] = useState<string>('');
  const [customSheetName, setCustomSheetName] = useState('');
  const [parsedOrders, setParsedOrders] = useState<any[]>([]);
  const [processingLog, setProcessingLog] = useState<string[]>([]);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const { progress, clientId, isConnected, connectionError } = useActionProgress();

  const { data: worksheetsData, isLoading: isLoadingWorksheets } = useQuery({
    queryKey: ['worksheets', sheetUrl],
    queryFn: () => fetchWorksheets(sheetUrl),
    enabled: !!sheetUrl,
  });

  const { mutate, isPending, data, error } = useMutation({
    mutationFn: (fileToProcess: File) => {
      const targetSheet = selectedWorksheet === 'custom' ? customSheetName : selectedWorksheet;
      return processFile(sheetUrl, action, fileToProcess, clientId, targetSheet || undefined);
    },
    onSuccess: (response) => {
      toast.success(response.message || 'File processed successfully!');
      setFile(null); // Clear file after successful upload
      // Invalidate relevant queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['orders-overview'] });
      queryClient.invalidateQueries({ queryKey: ['pending-orders'] });
      queryClient.invalidateQueries({ queryKey: ['all-orders'] });
    },
    onError: (err: any) => {
      const errorMessage = err.response?.data?.detail || err.message || 'An unknown error occurred.';
      toast.error(`Processing failed: ${errorMessage}`);
    },
  });

  useEffect(() => {
    if (data) {
        // Invalidate queries to refetch dashboard data after a successful action
        queryClient.invalidateQueries({ queryKey: ['orders-overview'] });
        queryClient.invalidateQueries({ queryKey: ['orders-overview-quick'] });
    }
  }, [data, queryClient]);

  // Listen for progress updates and extract parsed order data
  useEffect(() => {
    if (progress) {
      console.log('Progress update in Actions:', progress);
      
      // Add progress message to streaming log
      if (progress.message) {
        setProcessingLog(prev => {
          const newLog = [...prev, progress.message];
          // Keep only last 100 messages to prevent memory issues
          return newLog.slice(-100);
        });
      }
      
      // Check if this is an order_parsed message with actual order data
      if (progress.type === 'order_parsed' && progress.order) {
        console.log('Adding new order to table:', progress.order);
        setParsedOrders(prev => {
          // Check if order already exists
          const exists = prev.find(order => order.id === progress.order!.id);
          if (!exists) {
            const newOrders = [...prev, progress.order!];
            console.log('Updated parsed orders:', newOrders.length);
            return newOrders;
          }
          return prev;
        });
        
        // Add parsed order to log for streaming effect
        const orderLog = `✓ Parsed: ${progress.order.product} - $${progress.order.price} (Order #${progress.order.orderNumber})`;
        setProcessingLog(prev => {
          const newLog = [...prev, orderLog];
          return newLog.slice(-100);
        });
      }
    }
  }, [progress]);

  // Auto-scroll log to bottom when new messages arrive
  useEffect(() => {
    if (logContainerRef.current && processingLog.length > 0) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [processingLog]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
  });

  const handleProcessFile = () => {
    if (file) {
      if (selectedWorksheet === 'custom' && !customSheetName.trim()) {
        toast.error('Please enter a custom sheet name.');
        return;
      }
      // Clear previous data when starting new process
      setParsedOrders([]);
      setProcessingLog([]);
      mutate(file);
    } else {
      toast.error('Please select a file first.');
    }
  };
  
  const handleRemoveFile = () => {
    setFile(null);
  }

  if (!sheetUrl) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 text-center">
        <CubeTransparentIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">Google Sheet Not Connected</h3>
        <p className="mt-1 text-sm text-gray-500">Please set your Google Sheets URL in the settings to enable actions.</p>
        <div className="mt-6">
          <NavLink to="/settings" className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
            Go to Settings
          </NavLink>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Bot Actions</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Perform bulk operations by uploading a CSV or TXT file, just like with the Discord bot.
          </p>
        </div>
        
        {/* Connection Status - Moved to separate line */}
        <div className="mt-4 flex justify-end">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {isConnected ? 'Connected' : connectionError ? 'Connection Failed' : 'Connecting...'}
            </span>
          </div>
        </div>
        
        {isPending || data ? (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">Processing File...</h2>
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {progress ? `${progress.current} / ${progress.total} rows` : 'Initializing...'}
                </span>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-6">
              <div 
                className="bg-primary-600 h-2.5 rounded-full transition-all duration-300" 
                style={{ width: `${progress ? (progress.current / progress.total) * 100 : 0}%` }}
              ></div>
            </div>

            {/* Streaming Log Display - Like AI Thinking */}
            <div className="mt-6 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <div className="px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                  Processing Log
                </h3>
              </div>
              <div 
                ref={logContainerRef}
                className="h-96 overflow-y-auto p-4 font-mono text-xs text-gray-800 dark:text-gray-200 space-y-1 scroll-smooth"
              >
                {processingLog.length > 0 ? (
                  processingLog.map((log, index) => (
                    <div 
                      key={index} 
                      className="leading-relaxed"
                    >
                      <span className="text-gray-400 dark:text-gray-600 mr-2 select-none">{index + 1}.</span>
                      <span className="text-gray-700 dark:text-gray-300">{log}</span>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-600">
                    <div className="text-center">
                      <div className="animate-pulse mb-2 text-2xl">⏳</div>
                      <p>Waiting for processing to begin...</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-8 space-y-8">
            {/* Action Selector Buttons */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Action
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-1">
                {actionButtons.map((btn) => (
                  <button
                    key={btn.id}
                    onClick={() => setAction(btn.id)}
                    disabled={isPending}
                    className={`flex flex-col items-center justify-center p-4 rounded-lg transition-all duration-200 w-40 h-40
                      ${
                        action === btn.id
                          ? 'bg-blue-50 dark:bg-blue-900/30 border-2 border-blue-200 dark:border-blue-700 shadow-md scale-105'
                          : 'bg-white dark:bg-gray-700 border-2 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 hover:scale-105'
                      }`
                    }
                  >
                    <div className={`flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center mb-2
                      ${
                        action === btn.id
                          ? 'bg-blue-100 dark:bg-blue-800 border border-blue-300 dark:border-blue-600'
                          : 'bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500'
                      }`
                    }>
                      <btn.icon className={`h-6 w-6 ${
                        action === btn.id
                          ? 'text-blue-600 dark:text-blue-300'
                          : 'text-gray-600 dark:text-gray-400'
                      }`} />
                    </div>
                    <span className={`text-xs font-medium text-center ${
                      action === btn.id
                        ? 'text-blue-700 dark:text-blue-200'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {btn.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Worksheet Selector */}
            <div>
              <label htmlFor="worksheet-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Target Worksheet
              </label>
              <select
                id="worksheet-select"
                value={selectedWorksheet}
                onChange={(e) => setSelectedWorksheet(e.target.value)}
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                disabled={isPending || isLoadingWorksheets}
              >
                <option value="">Default (First Sheet)</option>
                {worksheetsData?.worksheets.map((ws) => (
                  <option key={ws.id} value={ws.title}>
                    {ws.title}
                  </option>
                ))}
                <option value="custom">-- Custom Sheet Name --</option>
              </select>
            </div>

            {/* Custom Sheet Name Input */}
            {selectedWorksheet === 'custom' && (
              <div>
                <label htmlFor="custom-sheet-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Custom Sheet Name
                </label>
                <input
                  type="text"
                  id="custom-sheet-name"
                  value={customSheetName}
                  onChange={(e) => setCustomSheetName(e.target.value)}
                  placeholder="Enter the exact name of the sheet"
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  disabled={isPending}
                />
              </div>
            )}

            {/* File Dropzone */}
            <div
              {...getRootProps()}
              className={`bg-gray-50 dark:bg-gray-800 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-primary-500 dark:border-primary-400 bg-primary-50 dark:bg-primary-900/20' : ''
              }`}
            >
              <input {...getInputProps()} />
              <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
              {file ? (
                <div className="mt-4 text-sm text-gray-600 dark:text-gray-300">
                  <p>Selected file: <span className="font-medium">{file.name}</span></p>
                  <p className="text-xs text-gray-500">{Math.round(file.size / 1024)} KB</p>
                </div>
              ) : (
                <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">
                  {isDragActive ? 'Drop the file here...' : 'Drag & drop a file here, or click to select'}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">.csv or .txt files only</p>
            </div>
            
            {file && !isPending && (
              <div className="flex justify-center">
                <button
                  onClick={handleRemoveFile}
                  className="text-sm font-medium text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                >
                  Remove File
                </button>
              </div>
            )}

            {/* Action Button */}
            <div className="flex justify-end">
              <button
                onClick={handleProcessFile}
                disabled={!file || isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isPending ? 'Processing...' : 'Process File'}
              </button>
            </div>

            {/* Progress Display */}
            {(isPending || parsedOrders.length > 0) && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-3"></div>
                    <div>
                      <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">Processing File...</h3>

                      {!progress && isPending && (
                        <p className="text-sm text-blue-700 dark:text-blue-300">
                          Connecting to server...
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {/* Connection Status */}
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {isConnected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                </div>
                
                {/* Progress Bar */}
                {progress && (
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-4">
                    <div 
                      className="bg-blue-600 h-3 rounded-full transition-all duration-300 flex items-center justify-center"
                      style={{ width: `${Math.max(5, (progress.current / progress.total) * 100)}%` }}
                    >
                      <span className="text-xs text-white font-medium">
                        {Math.round((progress.current / progress.total) * 100)}%
                      </span>
                    </div>
                  </div>
                )}
                
                {/* Fallback progress when no WebSocket */}
                {!progress && isPending && (
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-4">
                    <div className="bg-blue-600 h-3 rounded-full animate-pulse"></div>
                  </div>
                )}
                
                {/* Updated Status */}
                {progress && (
                  <p className="text-sm text-blue-700 dark:text-blue-300 mb-4">
                    {progress.message || 'Initializing...'}
                  </p>
                )}
                
                {/* Live Orders Table */}
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Parsed Orders ({parsedOrders.length})
                    </h4>
                    {progress && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {progress.current} / {progress.total} processed
                      </span>
                    )}
                  </div>
                  
                  {parsedOrders.length > 0 ? (
                    <div className="overflow-x-auto max-h-64 overflow-y-auto border rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              #
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Product
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Price
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Order #
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Email
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                          {parsedOrders.map((order, index) => (
                            <tr key={order.id || index} className="hover:bg-gray-50 dark:hover:bg-gray-800 animate-fade-in">
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 font-mono">
                                {index + 1}
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">
                                {order.product || 'N/A'}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 font-mono">
                                {order.price || 'N/A'}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 font-mono">
                                {order.orderNumber || 'N/A'}
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">
                                {order.email || 'N/A'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center">
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {isPending ? 'Waiting for orders to be parsed...' : 'No orders parsed yet'}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Result Display */}
            {data && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-4">
                <div className="flex items-center">
                  <CheckCircleIcon className="h-5 w-5 text-green-500 mr-3" />
                  <div>
                    <h3 className="text-sm font-medium text-green-800 dark:text-green-200">Processing Complete</h3>
                    <p className="text-sm text-green-700 dark:text-green-300">{(data as any)?.message || 'File processed successfully!'}</p>
                  </div>
                </div>
              </div>
            )}
            {error && (
               <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4">
                 <div className="flex items-center">
                   <XCircleIcon className="h-5 w-5 text-red-500 mr-3" />
                   <div>
                     <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
                     <p className="text-sm text-red-700 dark:text-red-300">{error?.message || 'An error occurred'}</p>
                   </div>
                 </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
