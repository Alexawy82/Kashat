'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { MapPin, Loader2, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { client } from '@/lib/api-client'

interface AddressSuggestion {
  display: string
  short: string
  street: string
  city: string
  state: string
  postcode: string
  country: string
  lat?: string
  lon?: string
}

interface AddressAutocompleteProps {
  value: string
  onChange: (value: string, details?: AddressSuggestion) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function AddressAutocomplete({
  value,
  onChange,
  placeholder = 'Start typing an address...',
  className,
  disabled,
}: AddressAutocompleteProps) {
  const [inputValue, setInputValue] = useState(value)
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Sync external value changes
  useEffect(() => {
    setInputValue(value)
  }, [value])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchSuggestions = useCallback(async (query: string) => {
    if (query.length < 3) {
      setSuggestions([])
      return
    }

    setIsLoading(true)
    try {
      const { data, error } = await client.get<{ suggestions: AddressSuggestion[] }>(
        `/api/networth/address/autocomplete?q=${encodeURIComponent(query)}`
      )
      if (!error && data?.suggestions) {
        setSuggestions(data.suggestions)
        setShowDropdown(data.suggestions.length > 0)
      }
    } catch (err) {
      console.error('Address autocomplete error:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setInputValue(newValue)
    setSelectedIndex(-1)

    // Debounce API calls (300ms)
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    debounceRef.current = setTimeout(() => {
      fetchSuggestions(newValue)
    }, 300)

    // Update parent with raw value (in case they don't select a suggestion)
    onChange(newValue)
  }

  const handleSelectSuggestion = (suggestion: AddressSuggestion) => {
    const formattedAddress = suggestion.short || suggestion.display
    setInputValue(formattedAddress)
    onChange(formattedAddress, suggestion)
    setShowDropdown(false)
    setSuggestions([])
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleSelectSuggestion(suggestions[selectedIndex])
        }
        break
      case 'Escape':
        setShowDropdown(false)
        break
    }
  }

  const handleClear = () => {
    setInputValue('')
    onChange('')
    setSuggestions([])
    setShowDropdown(false)
    inputRef.current?.focus()
  }

  return (
    <div className="relative">
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) setShowDropdown(true)
          }}
          placeholder={placeholder}
          className={cn('pl-9 pr-8', className)}
          disabled={disabled}
          autoComplete="off"
        />
        {isLoading && (
          <Loader2 className="absolute right-8 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
        )}
        {inputValue && !isLoading && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-muted rounded"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {showDropdown && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-auto"
        >
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleSelectSuggestion(suggestion)}
              className={cn(
                'w-full px-3 py-2 text-left text-sm hover:bg-accent transition-colors',
                'flex items-start gap-2',
                selectedIndex === index && 'bg-accent'
              )}
            >
              <MapPin className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{suggestion.short}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {suggestion.city}, {suggestion.state} {suggestion.postcode}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
