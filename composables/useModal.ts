import { useState } from '#app'

interface AlertOptions {
  title?: string
  type?: 'success' | 'error' | 'warning' | 'info'
}

interface AlertState {
  show: boolean
  title: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  resolve: (() => void) | null
}

interface ConfirmState {
  show: boolean
  title: string
  message: string
  resolve: ((value: boolean) => void) | null
}

export const useModal = () => {
  const alertState = useState<AlertState>('global-alert-state', () => ({
    show: false,
    title: '',
    message: '',
    type: 'info',
    resolve: null
  }))

  const confirmState = useState<ConfirmState>('global-confirm-state', () => ({
    show: false,
    title: '',
    message: '',
    resolve: null
  }))

  const showAlert = (message: string, options: AlertOptions = {}): Promise<void> => {
    const { title = '', type = 'info' } = options
    
    // 이전에 켜져 있던 게 있다면 즉시 닫고 resolve 해줌
    if (alertState.value.resolve) {
      alertState.value.resolve()
    }

    return new Promise<void>((resolve) => {
      alertState.value = {
        show: true,
        title,
        message,
        type,
        resolve: () => {
          alertState.value.show = false
          resolve()
        }
      }
    })
  }

  const showConfirm = (message: string, title: string = ''): Promise<boolean> => {
    if (confirmState.value.resolve) {
      confirmState.value.resolve(false)
    }

    return new Promise<boolean>((resolve) => {
      confirmState.value = {
        show: true,
        title,
        message,
        resolve: (value: boolean) => {
          confirmState.value.show = false
          resolve(value)
        }
      }
    })
  }

  return {
    alertState: readonly(alertState),
    confirmState: readonly(confirmState),
    showAlert,
    showConfirm,
    closeAlert: () => {
      if (alertState.value.resolve) alertState.value.resolve()
    },
    closeConfirm: (value: boolean) => {
      if (confirmState.value.resolve) confirmState.value.resolve(value)
    }
  }
}
