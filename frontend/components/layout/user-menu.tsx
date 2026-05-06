'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { DeleteAccountModal } from '@/components/auth/delete-account-modal';

export function UserMenu() {
  const { user, logout } = useAuth();
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  if (!user) return null;

  // Get user initials for avatar fallback
  const getInitials = (name: string | null, email: string) => {
    if (name) {
      return name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    return email[0].toUpperCase();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded-full">
          <Avatar>
            <AvatarFallback>
              {getInitials(user.display_name, user.email)}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">
              {user.display_name || 'User'}
            </p>
            <p className="text-xs text-gray-500">{user.email}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout}>
          Logout
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => setShowDeleteModal(true)}
          className="text-red-600 focus:text-red-600 focus:bg-red-50"
        >
          Delete account
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>

    {showDeleteModal && (
      <DeleteAccountModal onClose={() => setShowDeleteModal(false)} />
    )}
  );
}
