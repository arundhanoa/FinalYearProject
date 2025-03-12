    def _calculate_price_similarity(self, user_events, candidate_event):
        """
        Calculate similarity based on price type preference.
        Free events are considered more similar to each other, as are self-funded events.
        """
        if not user_events:
            # For new users, consider free events more attractive (higher similarity)
            return 1.0 if candidate_event.price_type == 'free' else 0.5
        
        # Count price types in user's history
        price_counts = {'free': 0, 'self-funded': 0}
        for event in user_events:
            if event.price_type in price_counts:
                price_counts[event.price_type] += 1
        
        # Calculate preference ratio (0 to 1 scale)
        total_events = len(user_events)
        if total_events == 0:
            return 0.5  # Neutral if no history
        
        preferred_count = price_counts.get(candidate_event.price_type, 0)
        price_preference = preferred_count / total_events
        
        # Return a score between 0.5 (no match) and 1.0 (perfect match)
        return 0.5 + (0.5 * price_preference) 