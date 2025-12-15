import { MapPin, Package, User, ChevronDown, ChevronUp } from 'lucide-react';
import { useShipments } from '../../hooks/useShipments';
import { useState } from 'react';

export function ShipmentTracking() {
  const { shipments = [] } = useShipments();
  const [expandedShipmentId, setExpandedShipmentId] = useState(null);

  const getStatusDisplay = (shipment) => {
    const aiStatus = shipment.aiApproval === 'approved' ? 'AI Approved' : 
                    shipment.aiApproval === 'rejected' ? 'AI Rejected' : 'AI Pending';
    const brokerStatus = shipment.brokerApproval === 'approved' ? 'Broker Approved' : 
                        shipment.brokerApproval === 'documents-requested' ? 'Docs Requested' : 'Broker Pending';
    const paymentStatus = shipment.paymentStatus === 'completed' ? 'Paid' : 'Payment Pending';
    
    return `${aiStatus} | ${brokerStatus} | ${paymentStatus}`;
  };

  const getAssignedBroker = (shipment) => {
    return shipment.brokerApproval !== 'not-started' ? 'John Broker' : 'Not Assigned';
  };

  const toggleExpanded = (shipmentId) => {
    setExpandedShipmentId(expandedShipmentId === shipmentId ? null : shipmentId);
  };

  return (
    <div style={{ background: '#FBF9F6', minHeight: '100vh', padding: 24 }}>
      <h1 className="mb-2" style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 10, fontSize: '1.5rem' }}>
        <MapPin className="w-6 h-6" style={{ color: '#3A2B28' }} />
        <span>Shipment Tracking Overview</span>
      </h1>
      <p className="text-slate-600 mb-8">Click on a shipment to view detailed shipper information</p>
      <div className="space-y-3">
        {shipments.map((shipment) => {
          const isExpanded = expandedShipmentId === shipment.id;
          const currencyCode = shipment.currency || 'USD';
          const currencySymbol = { USD: '$', EUR: '€', GBP: '£', JPY: '¥', CAD: 'C$', INR: '₹', CNY: '¥', AUD: 'A$' }[currencyCode] || currencyCode;

          return (
            <div key={shipment.id} className="bg-white rounded-xl overflow-hidden border-2" style={{ borderColor: '#3A2B28' }}>
              {/* Main Row - Clickable */}
              <div
                onClick={() => toggleExpanded(shipment.id)}
                className="p-4 cursor-pointer hover:bg-slate-50 transition-colors"
                style={{ background: isExpanded ? '#F5F0ED' : 'white' }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <button className="p-1 hover:bg-slate-200 rounded">
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5" style={{ color: '#3A2B28' }} />
                      ) : (
                        <ChevronDown className="w-5 h-5" style={{ color: '#3A2B28' }} />
                      )}
                    </button>
                    
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: '#D4AFA0' }}>
                        <Package className="w-5 h-5" style={{ color: '#2F1B17' }} />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">Shipment #{shipment.id}</p>
                        <p className="text-sm text-slate-600">
                          {shipment.shipper?.city || 'N/A'}, {shipment.shipper?.country || ''} → {shipment.consignee?.city || 'N/A'}, {shipment.consignee?.country || ''}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 ml-auto">
                      <div className="text-right hidden md:block">
                        <p className="text-xs text-slate-500">Pickup Mode</p>
                        <p className="text-sm font-medium text-slate-900">{shipment.pickupType || 'N/A'}</p>
                      </div>
                      <div className="text-right hidden lg:block">
                        <p className="text-xs text-slate-500">Broker</p>
                        <div className="flex items-center gap-1">
                          <User className="w-4 h-4 text-slate-700" />
                          <p className="text-sm font-medium text-slate-900">{getAssignedBroker(shipment)}</p>
                        </div>
                      </div>
                      <div className="text-right hidden lg:block">
                        <p className="text-xs text-slate-500">Status</p>
                        <p className="text-xs font-medium text-slate-700">{getStatusDisplay(shipment)}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Expanded Details Section */}
              {isExpanded && (
                <div className="border-t-2" style={{ borderColor: '#E6B6A0' }}>
                  <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Shipper Details */}
                    <div className="space-y-4">
                      <div>
                        <h3 className="font-semibold text-slate-900 mb-4" style={{ color: '#2F1B17' }}>Shipper Details</h3>
                        <div className="space-y-3 bg-slate-50 p-4 rounded-lg">
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Company</p>
                            <p className="text-slate-900 font-medium">{shipment.shipper?.company || shipment.shipperName || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Contact Person</p>
                            <p className="text-slate-900">{shipment.shipper?.contactName || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Email</p>
                            <p className="text-slate-900">{shipment.shipper?.email || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Phone</p>
                            <p className="text-slate-900">{shipment.shipper?.phone || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Address</p>
                            <p className="text-slate-900">
                              {shipment.shipper?.address || 'N/A'}, {shipment.shipper?.city || ''}, {shipment.shipper?.state || ''} {shipment.shipper?.postalCode || ''}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Country</p>
                            <p className="text-slate-900">{shipment.shipper?.country || 'N/A'}</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Shipment Details */}
                    <div className="space-y-4">
                      <div>
                        <h3 className="font-semibold text-slate-900 mb-4" style={{ color: '#2F1B17' }}>Shipment Details</h3>
                        <div className="space-y-3 bg-slate-50 p-4 rounded-lg">
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Shipment ID</p>
                            <p className="text-slate-900 font-mono">#{shipment.id}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Total Value</p>
                            <p className="text-slate-900 font-medium">{currencySymbol}{parseFloat(shipment.value || 0).toLocaleString()} {currencyCode}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Pickup Type</p>
                            <p className="text-slate-900">{shipment.pickupType || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-600 uppercase tracking-wide">Destination</p>
                            <p className="text-slate-900">
                              {shipment.consignee?.city || 'N/A'}, {shipment.consignee?.country || 'N/A'}
                            </p>
                          </div>
                          <div className="pt-2">
                            <p className="text-xs text-slate-600 uppercase tracking-wide mb-2">Approval Status</p>
                            <div className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-slate-700">AI Review:</span>
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  shipment.aiApproval === 'approved' ? 'bg-green-100 text-green-700' :
                                  shipment.aiApproval === 'rejected' ? 'bg-red-100 text-red-700' :
                                  'bg-yellow-100 text-yellow-700'
                                }`}>
                                  {shipment.aiApproval === 'approved' ? 'Approved' :
                                   shipment.aiApproval === 'rejected' ? 'Rejected' : 'Pending'}
                                </span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-slate-700">Broker Review:</span>
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  shipment.brokerApproval === 'approved' ? 'bg-green-100 text-green-700' :
                                  shipment.brokerApproval === 'documents-requested' ? 'bg-blue-100 text-blue-700' :
                                  shipment.brokerApproval === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-slate-100 text-slate-700'
                                }`}>
                                  {shipment.brokerApproval === 'approved' ? 'Approved' :
                                   shipment.brokerApproval === 'documents-requested' ? 'Docs Requested' :
                                   shipment.brokerApproval === 'pending' ? 'Pending' : 'Not Started'}
                                </span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-slate-700">Payment:</span>
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  shipment.paymentStatus === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>
                                  {shipment.paymentStatus === 'completed' ? 'Paid' : 'Pending'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {shipments.length === 0 && (
          <div className="bg-white rounded-xl p-8 text-center">
            <Package className="w-12 h-12 mx-auto text-slate-300 mb-3" />
            <p className="text-slate-600">No shipments found</p>
          </div>
        )}
      </div>
    </div>
  );
}

