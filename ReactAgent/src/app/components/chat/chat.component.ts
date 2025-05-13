import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';
import { Subscription } from 'rxjs';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

// Pipe for safe HTML
import { Pipe, PipeTransform } from '@angular/core';
@Pipe({ name: 'safeHtml', standalone: true })
export class SafeHtmlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}
  transform(value: string): SafeHtml {
    // Basic sanitization: Allow common formatting tags, links, code blocks.
    // Adjust the regex as needed for more/less restrictive sanitization.
    // THIS IS A BASIC EXAMPLE AND MAY NEED ROBUST SANITIZATION IN PRODUCTION.
    // const sanitized = value.replace(/<script.*?>.*?<\/script>/gi, ''); // Remove scripts
    // Consider using a library like DOMPurify for robust sanitization.
    return this.sanitizer.bypassSecurityTrustHtml(value);
  }
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, SafeHtmlPipe],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messageContainer') private messageContainer!: ElementRef;

  userMessage = '';
  messages: {content: string, sender: 'user' | 'agent', thinking?: string}[] = [];
  isLoading = false;
  isConnected = false;
  connectionError = '';
  private subscriptions: Subscription[] = [];
  private shouldScrollToBottom = false;

  constructor(
    private chatService: ChatService,
    private sanitizer: DomSanitizer,
    private cdRef: ChangeDetectorRef
  ) {
    console.log('>>> ChatComponent constructor running!');
  }

  ngOnInit(): void {
    console.log('>>> ChatComponent ngOnInit');
    this.subscriptions.push(
      this.chatService.getConnectionStatus().subscribe((status) => {
        console.log('Connection status:', status);
        this.isConnected = status.connected;
        this.connectionError = status.error || '';
        this.cdRef.detectChanges();
      })
    );

    this.subscriptions.push(
      this.chatService.getMessage().subscribe((message) => {
        console.log('Received message:', message);
        const existingAgentMessage = this.findLastAgentMessage();
        if (existingAgentMessage && !existingAgentMessage.content) {
          existingAgentMessage.content = message.content;
        } else {
          this.messages.push({content: message.content, sender: 'agent'});
        }
        this.isLoading = false;
        this.shouldScrollToBottom = true;
        this.cdRef.detectChanges();
      })
    );

    this.subscriptions.push(
      this.chatService.getThinking().subscribe((thinkingStep) => {
        console.log('Received thinking step:', thinkingStep);
        const lastAgentMessage = this.findLastAgentMessage();

        if (thinkingStep === '') {
          if(lastAgentMessage) {
            lastAgentMessage.thinking = undefined;
          }
          this.isLoading = false;
        } else if (lastAgentMessage) {
          lastAgentMessage.thinking = (lastAgentMessage.thinking ? lastAgentMessage.thinking + '\n\n' : '') + thinkingStep;
          if (!lastAgentMessage.content) {
            lastAgentMessage.content = '';
          }
          this.isLoading = true;
        } else {
          this.messages.push({content: '', sender: 'agent', thinking: thinkingStep});
          this.isLoading = true;
        }
        
        this.shouldScrollToBottom = true;
        this.cdRef.detectChanges();
      })
    );
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  ngOnDestroy(): void {
    console.log('>>> ChatComponent ngOnDestroy');
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  sendMessage(): void {
    const trimmedMessage = this.userMessage.trim();
    if (trimmedMessage === '' || !this.isConnected) return;

    this.messages.push({content: trimmedMessage, sender: 'user'});
    this.messages.push({content: '', sender: 'agent', thinking: '...'});
    this.isLoading = true;
    this.shouldScrollToBottom = true;
    this.chatService.sendMessage(trimmedMessage);
    this.userMessage = '';
    this.resetTextareaHeight();
    this.cdRef.detectChanges();
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  autoResize(textarea: HTMLTextAreaElement): void {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
  }

  resetTextareaHeight(): void {
    const textarea = document.querySelector('.message-input') as HTMLTextAreaElement;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = '40px';
    }
  }

  private scrollToBottom(): void {
    try {
      this.messageContainer.nativeElement.scrollTop = this.messageContainer.nativeElement.scrollHeight;
    } catch (err) {
      console.error('Could not scroll to bottom:', err);
    }
  }

  private findLastAgentMessage(): {content: string, sender: 'user' | 'agent', thinking?: string} | undefined {
    for (let i = this.messages.length - 1; i >= 0; i--) {
      if (this.messages[i].sender === 'agent') {
        return this.messages[i];
      }
    }
    return undefined;
  }
} 