import { useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { XMarkIcon } from '@heroicons/react/24/outline'

interface OrderData {
  [key: string]: any
}

interface MobileOrderCardProps {
  order: OrderData
  onEdit: (column: string, value: string) => void
}

export default function MobileOrderCard({ order, onEdit }: MobileOrderCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showAllFields, setShowAllFields] = useState(false)

  function closeModal() {
    setIsOpen(false)
  }

  function openModal() {
    setIsOpen(true)
  }

  return (
    <>
      {/* Card View */}
      <div 
        className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-3 cursor-pointer active:bg-gray-50 dark:active:bg-gray-700"
        onClick={openModal}
      >
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
              {order.Product || 'No Product Name'}
            </h3>
          </div>
          <span className={`ml-2 text-xs px-2 py-1 rounded flex-shrink-0 ${
            order.Status?.toUpperCase() === 'VERIFIED' 
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' 
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
          }`}>
            {order.Status || 'No Status'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="text-gray-600 dark:text-gray-400 truncate">
            #{order['Order Number'] || 'No Order Number'}
          </div>
          {order['Tracking Number'] && (
            <div className="text-blue-600 dark:text-blue-400 truncate ml-2">
              {order['Tracking Number']}
            </div>
          )}
        </div>
      </div>

      {/* Modal View */}
      <Transition appear show={isOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={closeModal}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black bg-opacity-25" />
          </Transition.Child>

          <div className="fixed inset-0 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4">
              <Transition.Child
                as={Fragment}
                enter="ease-out duration-300"
                enterFrom="opacity-0 scale-95"
                enterTo="opacity-100 scale-100"
                leave="ease-in duration-200"
                leaveFrom="opacity-100 scale-100"
                leaveTo="opacity-0 scale-95"
              >
                <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 p-6 text-left align-middle shadow-xl transition-all">
                  <Dialog.Title
                    as="h3"
                    className="text-lg font-medium leading-6 text-gray-900 dark:text-gray-100 mb-4 pr-8"
                  >
                    Order Details
                    <button
                      onClick={closeModal}
                      className="absolute top-4 right-4 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                    >
                      <XMarkIcon className="h-6 w-6" />
                    </button>
                  </Dialog.Title>

                  <div className="mt-2 space-y-4">
                    {/* Important fields first */}
                    {['Product', 'Order Number', 'Status', 'Tracking Number', 'Quantity', 'Price'].map((key) => {
                      if (!(key in order)) return null;
                      return (
                        <div key={key} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            {key}
                          </label>
                          <input
                            type="text"
                            value={order[key] || ''}
                            onChange={(e) => onEdit(key, e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>
                      );
                    })}
                    
                    {/* Show remaining fields in a collapsible section */}
                    <div className="mt-6">
                      <button
                        type="button"
                        onClick={() => setShowAllFields(!showAllFields)}
                        className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                      >
                        {showAllFields ? 'Show Less' : 'Show All Fields'} ▾
                      </button>
                      
                      {showAllFields && (
                        <div className="mt-4 space-y-4">
                          {Object.entries(order).map(([key, value]) => {
                            if (['Product', 'Order Number', 'Status', 'Tracking Number', 'Quantity', 'Price'].includes(key)) return null;
                            return (
                              <div key={key} className="border-b border-gray-200 dark:border-gray-700 pb-3">
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                  {key}
                                </label>
                                <input
                                  type="text"
                                  value={value || ''}
                                  onChange={(e) => onEdit(key, e.target.value)}
                                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                                />
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </>
  )
}
