import React, { useState, useEffect } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, MessageSquare, Brain, Users, MapPin, Clock, Phone, Check, X } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface AssignmentSuggestion {
  order_id: number;
  driver_id: number;
  driver_name: string;
  distance_km: number;
  confidence: string;
  reasoning: string;
}

interface AIAssignmentResponse {
  suggestions: AssignmentSuggestion[];
  method: string;
  available_drivers_count: number;
  pending_orders_count: number;
  scheduled_drivers_count?: number;
  total_drivers_count?: number;
  ai_reasoning?: string;
}

interface PendingOrder {
  order_id: number;
  customer_name?: string;
  delivery_address?: string;
  estimated_lat: number;
  estimated_lng: number;
  total_value: number;
  priority: string;
  delivery_date?: string;
}

interface AvailableDriver {
  driver_id: number;
  driver_name: string;
  phone?: string;
  shift_id: number;
  clock_in_location?: string;
  clock_in_lat: number;
  clock_in_lng: number;
  is_outstation: boolean;
  current_active_trips: number;
  hours_worked: number;
}

interface ParsedOrderInfo {
  customerName: string;
  customerPhone?: string;
  deliveryAddress: string;
  notes?: string;
  totalAmount: number;
}

export default function AIAssignmentsPage() {
  const [activeTab, setActiveTab] = useState('orders');
  const [messageText, setMessageText] = useState('');
  const [parsedOrder, setParsedOrder] = useState<ParsedOrderInfo | null>(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const queryClient = useQueryClient();

  // Queries
  const { data: aiSuggestions, isLoading: loadingSuggestions, refetch: refetchSuggestions } = useQuery<AIAssignmentResponse>({
    queryKey: ['ai-assignments'],
    queryFn: async () => {
      const response = await fetch('/_api/ai-assignments/suggestions');
      if (!response.ok) throw new Error('Failed to fetch AI suggestions');
      return response.json();
    }
  });

  const { data: pendingOrders, isLoading: loadingOrders, refetch: refetchOrders } = useQuery<{pending_orders: PendingOrder[]}>({
    queryKey: ['pending-orders'],
    queryFn: async () => {
      const response = await fetch('/_api/ai-assignments/pending-orders');
      if (!response.ok) throw new Error('Failed to fetch pending orders');
      return response.json();
    }
  });

  const { data: availableDrivers, isLoading: loadingDrivers, refetch: refetchDrivers } = useQuery<{available_drivers: AvailableDriver[]}>({
    queryKey: ['available-drivers'],
    queryFn: async () => {
      const response = await fetch('/_api/ai-assignments/available-drivers');
      if (!response.ok) throw new Error('Failed to fetch available drivers');
      return response.json();
    }
  });

  // Mutations
  const createOrderMutation = useMutation({
    mutationFn: async (order: ParsedOrderInfo) => {
      const response = await fetch('/_api/orders/simple', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: order.customerName,
          customer_phone: order.customerPhone,
          delivery_address: order.deliveryAddress,
          notes: order.notes,
          total_amount: order.totalAmount
        })
      });
      if (!response.ok) throw new Error('Failed to create order');
      return response.json();
    },
    onSuccess: (data) => {
      setSuccessMessage(`Order #${data.id} created successfully!`);
      setMessageText('');
      setParsedOrder(null);
      queryClient.invalidateQueries({ queryKey: ['pending-orders'] });
      setTimeout(() => setSuccessMessage(''), 3000);
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Failed to create order');
    }
  });

  const acceptAllMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/_api/ai-assignments/accept-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to accept assignments: ${response.status} ${errorText}`);
      }
      return response.json();
    },
    onSuccess: (data) => {
      setSuccessMessage(data.message);
      queryClient.invalidateQueries({ queryKey: ['ai-assignments'] });
      queryClient.invalidateQueries({ queryKey: ['pending-orders'] });
      setTimeout(() => setSuccessMessage(''), 5000);
    },
    onError: (error: any) => {
      setErrorMessage(error.message || 'Failed to accept all assignments');
    }
  });

  // Parse message helper
  const parseMessage = (message: string): ParsedOrderInfo | null => {
    try {
      const lines = message.trim().split('\n').map(l => l.trim());
      let customerName = '';
      let customerPhone: string | undefined;
      let deliveryAddress = '';
      let notes = '';
      let totalAmount = 0;

      for (const line of lines) {
        const lowerLine = line.toLowerCase();
        if (lowerLine.startsWith('name:') || lowerLine.startsWith('customer:')) {
          customerName = line.split(':')[1]?.trim() || '';
        } else if (lowerLine.startsWith('phone:') || lowerLine.startsWith('tel:') || lowerLine.startsWith('contact:')) {
          customerPhone = line.split(':')[1]?.trim()
            .replace(/\+6/g, '').replace(/-/g, '').replace(/\s/g, '');
          if (customerPhone?.startsWith('01') && customerPhone.length >= 10) {
            customerPhone = '6' + customerPhone;
          }
        } else if (lowerLine.startsWith('address:') || lowerLine.startsWith('location:')) {
          deliveryAddress = line.split(':')[1]?.trim() || '';
        } else if (lowerLine.startsWith('amount:') || lowerLine.startsWith('total:') || lowerLine.startsWith('price:')) {
          const amountStr = line.split(':')[1]?.trim()
            .replace(/rm/gi, '').replace(',', '').trim();
          totalAmount = parseFloat(amountStr) || 0;
        } else if (lowerLine.startsWith('notes:') || lowerLine.startsWith('remarks:')) {
          notes = line.split(':')[1]?.trim() || '';
        }
      }

      if (customerName && deliveryAddress) {
        return {
          customerName,
          customerPhone,
          deliveryAddress,
          notes: notes || undefined,
          totalAmount
        };
      }
      return null;
    } catch {
      return null;
    }
  };

  const handleParseMessage = () => {
    const parsed = parseMessage(messageText);
    setParsedOrder(parsed);
    if (!parsed) {
      setErrorMessage('Could not parse message. Please check the format.');
    } else {
      setErrorMessage('');
    }
  };

  const handleCreateOrder = () => {
    if (parsedOrder) {
      createOrderMutation.mutate(parsedOrder);
    }
  };

  const handleAcceptAll = () => {
    acceptAllMutation.mutate();
  };

  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setErrorMessage(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [errorMessage]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Assignment Management</h1>
        <p className="text-gray-600">Manage orders, accept AI suggestions, and assign deliveries to drivers.</p>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <Alert className="border-green-200 bg-green-50">
          <Check className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-700">{successMessage}</AlertDescription>
        </Alert>
      )}
      
      {errorMessage && (
        <Alert className="border-red-200 bg-red-50">
          <X className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-700">{errorMessage}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="orders" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Order Management
          </TabsTrigger>
          <TabsTrigger value="ai-suggestions" className="flex items-center gap-2">
            <Brain className="h-4 w-4" />
            AI Suggestions
          </TabsTrigger>
          <TabsTrigger value="assignments" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Assignments
          </TabsTrigger>
        </TabsList>

        {/* Order Management Tab */}
        <TabsContent value="orders" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Message Parsing */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Create Order from Message
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Paste WhatsApp message or order details:</label>
                  <Textarea
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    placeholder={`Example:
Name: John Doe
Phone: 0123456789
Address: 123 Main St, KL
Amount: RM 150.00
Notes: Urgent delivery`}
                    className="h-32"
                  />
                </div>

                <div className="flex gap-2">
                  <Button onClick={handleParseMessage} disabled={!messageText.trim()}>
                    Parse Message
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => {
                      setMessageText('');
                      setParsedOrder(null);
                      setErrorMessage('');
                    }}
                  >
                    Clear
                  </Button>
                </div>

                {/* Parsed Preview */}
                {parsedOrder && (
                  <Card className="bg-blue-50 border-blue-200">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-blue-700 text-sm">Parsed Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <span className="font-medium">Customer:</span>
                        <span className="col-span-2">{parsedOrder.customerName}</span>
                        
                        {parsedOrder.customerPhone && (
                          <>
                            <span className="font-medium">Phone:</span>
                            <span className="col-span-2">{parsedOrder.customerPhone}</span>
                          </>
                        )}
                        
                        <span className="font-medium">Address:</span>
                        <span className="col-span-2">{parsedOrder.deliveryAddress}</span>
                        
                        {parsedOrder.totalAmount > 0 && (
                          <>
                            <span className="font-medium">Amount:</span>
                            <span className="col-span-2">RM {parsedOrder.totalAmount}</span>
                          </>
                        )}
                        
                        {parsedOrder.notes && (
                          <>
                            <span className="font-medium">Notes:</span>
                            <span className="col-span-2">{parsedOrder.notes}</span>
                          </>
                        )}
                      </div>
                      
                      <Button 
                        onClick={handleCreateOrder}
                        disabled={createOrderMutation.isPending}
                        className="w-full mt-4"
                      >
                        {createOrderMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create Order
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </CardContent>
            </Card>

            {/* Pending Orders */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Pending Orders</CardTitle>
                <Button variant="outline" size="sm" onClick={() => refetchOrders()}>
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {loadingOrders ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : pendingOrders?.pending_orders.length ? (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {pendingOrders.pending_orders.map((order) => (
                      <div key={order.order_id} className="p-3 border rounded-md">
                        <div className="flex justify-between items-start mb-2">
                          <span className="font-medium">Order #{order.order_id}</span>
                          <Badge variant={order.priority === 'urgent' ? 'destructive' : order.priority === 'high' ? 'default' : 'secondary'}>
                            {order.priority.toUpperCase()}
                          </Badge>
                        </div>
                        {order.customer_name && (
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <Users className="h-3 w-3" />
                            {order.customer_name}
                          </div>
                        )}
                        {order.delivery_address && (
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <MapPin className="h-3 w-3" />
                            {order.delivery_address}
                          </div>
                        )}
                        {order.total_value > 0 && (
                          <div className="text-sm font-medium text-green-600">
                            RM {order.total_value}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No pending orders</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* AI Suggestions Tab - SIMPLIFIED */}
        <TabsContent value="ai-suggestions" className="space-y-6">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <Brain className="h-16 w-16 mx-auto mb-4 text-blue-600" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">AI Assignment Engine</h2>
              <p className="text-gray-600">Let AI automatically assign all pending orders to the best available drivers</p>
            </div>

            {loadingSuggestions ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-600">Analyzing assignments...</span>
              </div>
            ) : (
              <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
                <CardContent className="p-8 text-center">
                  {aiSuggestions && (
                    <div className="grid grid-cols-3 gap-6 mb-6">
                      <div>
                        <div className="text-3xl font-bold text-blue-900">{aiSuggestions.available_drivers_count}</div>
                        <div className="text-sm text-blue-700">Available Drivers</div>
                      </div>
                      <div>
                        <div className="text-3xl font-bold text-blue-900">{aiSuggestions.pending_orders_count}</div>
                        <div className="text-sm text-blue-700">Pending Orders</div>
                      </div>
                      <div>
                        <div className="text-3xl font-bold text-blue-900">{aiSuggestions.suggestions.length}</div>
                        <div className="text-sm text-blue-700">Ready to Assign</div>
                      </div>
                    </div>
                  )}
                  
                  <div className="space-y-4">
                    <Button 
                      onClick={handleAcceptAll}
                      disabled={acceptAllMutation.isPending || !aiSuggestions?.suggestions.length}
                      className="w-full max-w-md h-14 text-lg"
                    >
                      {acceptAllMutation.isPending ? (
                        <>
                          <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                          Assigning Orders...
                        </>
                      ) : (
                        <>
                          <Check className="mr-3 h-5 w-5" />
                          Accept All Suggestions ({aiSuggestions?.suggestions.length || 0})
                        </>
                      )}
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      onClick={() => refetchSuggestions()} 
                      disabled={loadingSuggestions}
                    >
                      {loadingSuggestions && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Refresh Suggestions
                    </Button>
                  </div>

                  {!aiSuggestions?.suggestions.length && aiSuggestions && (
                    <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-yellow-800 text-sm">
                        {aiSuggestions.pending_orders_count === 0 
                          ? "No pending orders to assign" 
                          : aiSuggestions.available_drivers_count === 0
                          ? "No drivers available - schedule drivers first"
                          : "Unable to generate suggestions - check driver schedules"}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Assignments Tab */}
        <TabsContent value="assignments" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Available Drivers */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Available Drivers</CardTitle>
                <Button variant="outline" size="sm" onClick={() => refetchDrivers()}>
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {loadingDrivers ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : availableDrivers?.available_drivers.length ? (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {availableDrivers.available_drivers.map((driver) => (
                      <div key={driver.driver_id} className="p-3 border rounded-md">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <span className="font-medium">{driver.driver_name}</span>
                            {driver.is_outstation && (
                              <Badge variant="secondary" className="ml-2">OUTSTATION</Badge>
                            )}
                          </div>
                          <Badge variant={driver.current_active_trips >= 3 ? 'destructive' : driver.current_active_trips >= 2 ? 'default' : 'secondary'}>
                            {driver.current_active_trips} active
                          </Badge>
                        </div>
                        
                        {driver.clock_in_location && (
                          <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                            <MapPin className="h-3 w-3" />
                            {driver.clock_in_location}
                          </div>
                        )}
                        
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {Math.round(driver.hours_worked)}h worked
                          </div>
                          {driver.phone && (
                            <div className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {driver.phone}
                            </div>
                          )}
                        </div>
                        
                        {/* Workload indicator */}
                        <div className="mt-2">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full ${
                                driver.current_active_trips >= 3 ? 'bg-red-500' : 
                                driver.current_active_trips >= 2 ? 'bg-yellow-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min((driver.current_active_trips / 3) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No drivers clocked in</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Current Assignments Placeholder */}
            <Card>
              <CardHeader>
                <CardTitle>Current Assignments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500">
                  <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Assignment management coming soon...</p>
                  <p className="text-sm">View and edit current trip assignments</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

(AIAssignmentsPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;