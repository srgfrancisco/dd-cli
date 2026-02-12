"""Tests for tag processing utilities."""

from ddg.utils.tags import parse_tags, format_tags_for_display


class TestParseTags:
    """Test suite for parse_tags function."""

    def test_basic_tag_parsing(self):
        """Test basic comma-separated tag parsing."""
        result = parse_tags("service:web,env:prod,team:platform")
        expected = ["env:prod", "service:web", "team:platform"]  # Sorted
        assert result == expected

    def test_whitespace_stripping(self):
        """Test that whitespace around tags is stripped."""
        # Leading/trailing spaces
        result = parse_tags(" service:web , env:prod , team:platform ")
        expected = ["env:prod", "service:web", "team:platform"]
        assert result == expected

        # Mixed whitespace
        result = parse_tags("service:web,  env:prod  ,team:platform")
        expected = ["env:prod", "service:web", "team:platform"]
        assert result == expected

    def test_deduplication(self):
        """Test that duplicate tags are removed."""
        result = parse_tags("service:web,env:prod,service:web,team:platform,env:prod")
        # Should have no duplicates
        expected = ["env:prod", "service:web", "team:platform"]
        assert result == expected
        assert len(result) == 3

    def test_empty_string(self):
        """Test that empty string returns empty list."""
        result = parse_tags("")
        assert result == []

    def test_whitespace_only(self):
        """Test that whitespace-only string returns empty list."""
        result = parse_tags("   ")
        assert result == []

        result = parse_tags("\t\n  ")
        assert result == []

    def test_single_tag(self):
        """Test parsing a single tag."""
        result = parse_tags("service:web")
        assert result == ["service:web"]

    def test_tags_with_empty_entries(self):
        """Test that empty entries between commas are ignored."""
        # Double comma
        result = parse_tags("service:web,,env:prod")
        expected = ["env:prod", "service:web"]
        assert result == expected

        # Leading comma
        result = parse_tags(",service:web,env:prod")
        expected = ["env:prod", "service:web"]
        assert result == expected

        # Trailing comma
        result = parse_tags("service:web,env:prod,")
        expected = ["env:prod", "service:web"]
        assert result == expected

        # Multiple empty entries
        result = parse_tags("service:web,,,env:prod,,team:platform,")
        expected = ["env:prod", "service:web", "team:platform"]
        assert result == expected

    def test_sorting_consistency(self):
        """Test that tags are consistently sorted."""
        # Different input orders should produce same output
        result1 = parse_tags("zulu:1,alpha:2,bravo:3")
        result2 = parse_tags("bravo:3,zulu:1,alpha:2")
        result3 = parse_tags("alpha:2,bravo:3,zulu:1")

        expected = ["alpha:2", "bravo:3", "zulu:1"]

        assert result1 == expected
        assert result2 == expected
        assert result3 == expected

    def test_special_characters_in_tags(self):
        """Test tags with special characters."""
        # Underscores, hyphens, dots
        result = parse_tags("service:web-api,env:prod_us,version:1.2.3")
        expected = ["env:prod_us", "service:web-api", "version:1.2.3"]
        assert result == expected

        # URL-like values
        result = parse_tags("url:https://example.com,path:/api/v1")
        assert "url:https://example.com" in result
        assert "path:/api/v1" in result

    def test_tags_without_colons(self):
        """Test tags that don't follow key:value format."""
        result = parse_tags("production,critical,monitoring")
        expected = ["critical", "monitoring", "production"]
        assert result == expected

    def test_mixed_tag_formats(self):
        """Test mix of key:value and plain tags."""
        result = parse_tags("service:web,production,env:prod,critical")
        expected = ["critical", "env:prod", "production", "service:web"]
        assert result == expected

    def test_unicode_tags(self):
        """Test tags with unicode characters."""
        result = parse_tags("service:web,region:🌎,team:plataforma")
        assert len(result) == 3
        assert "region:🌎" in result
        assert "team:plataforma" in result

    def test_very_long_tag_string(self):
        """Test parsing a large number of tags."""
        # Create 100 tags
        tags_list = [f"tag{i}:value{i}" for i in range(100)]
        tags_str = ",".join(tags_list)

        result = parse_tags(tags_str)

        assert len(result) == 100
        # Should be sorted
        assert result == sorted(tags_list)

    def test_tags_with_spaces_in_values(self):
        """Test that tags with spaces in values are preserved."""
        # Note: This might not be valid Datadog tag format, but function should handle it
        result = parse_tags("name:Web Server,location:New York")
        # Spaces are stripped from around commas, not within tag values
        assert "name:Web Server" in result
        assert "location:New York" in result

    def test_case_sensitivity(self):
        """Test that tag parsing is case-sensitive."""
        result = parse_tags("Service:Web,service:web,SERVICE:WEB")
        # All three are different due to case
        assert len(result) == 3
        assert "SERVICE:WEB" in result
        assert "Service:Web" in result
        assert "service:web" in result


class TestFormatTagsForDisplay:
    """Test suite for format_tags_for_display function."""

    def test_empty_list(self):
        """Test formatting empty tag list."""
        result = format_tags_for_display([])
        assert result == ""

    def test_single_tag(self):
        """Test formatting single tag."""
        result = format_tags_for_display(["service:web"])
        assert result == "service:web"

    def test_tags_within_limit(self):
        """Test formatting when tag count is within max_tags limit."""
        tags = ["service:web", "env:prod", "team:platform"]
        result = format_tags_for_display(tags, max_tags=3)
        assert result == "service:web, env:prod, team:platform"

        # Exactly at limit
        result = format_tags_for_display(tags, max_tags=3)
        assert result == "service:web, env:prod, team:platform"

    def test_tags_exceed_limit(self):
        """Test formatting when tag count exceeds max_tags limit."""
        tags = ["service:web", "env:prod", "team:platform", "region:us-west", "version:1.0"]

        # Show first 3 tags
        result = format_tags_for_display(tags, max_tags=3)
        assert result == "service:web, env:prod, team:platform, +2 more"

        # Show first 2 tags
        result = format_tags_for_display(tags, max_tags=2)
        assert result == "service:web, env:prod, +3 more"

        # Show first 1 tag
        result = format_tags_for_display(tags, max_tags=1)
        assert result == "service:web, +4 more"

    def test_default_max_tags(self):
        """Test that default max_tags is 3."""
        tags = ["tag1", "tag2", "tag3", "tag4", "tag5"]

        # Default should be 3
        result = format_tags_for_display(tags)
        assert result == "tag1, tag2, tag3, +2 more"

    def test_max_tags_zero(self):
        """Test edge case with max_tags=0."""
        tags = ["service:web", "env:prod", "team:platform"]
        result = format_tags_for_display(tags, max_tags=0)
        # Should show 0 tags plus count of remaining
        assert result == ", +3 more"

    def test_max_tags_negative(self):
        """Test edge case with negative max_tags."""
        tags = ["service:web", "env:prod", "team:platform"]
        result = format_tags_for_display(tags, max_tags=-1)
        # Negative slicing should show nothing
        assert ", +" in result or result.startswith(", +")

    def test_max_tags_exceeds_list_length(self):
        """Test when max_tags is greater than number of tags."""
        tags = ["service:web", "env:prod"]
        result = format_tags_for_display(tags, max_tags=10)
        # Should show all tags without "+X more"
        assert result == "service:web, env:prod"

    def test_one_tag_over_limit(self):
        """Test when there's exactly one tag over the limit."""
        tags = ["service:web", "env:prod", "team:platform", "region:us"]
        result = format_tags_for_display(tags, max_tags=3)
        # Should say "+1 more" not "+1 more" (grammatically correct)
        assert result == "service:web, env:prod, team:platform, +1 more"

    def test_preserves_tag_order(self):
        """Test that original tag order is preserved in display."""
        # Tags in specific order
        tags = ["zebra", "alpha", "beta"]
        result = format_tags_for_display(tags, max_tags=2)
        # Should show first 2 in original order
        assert result.startswith("zebra, alpha")

    def test_formatting_with_long_tag_names(self):
        """Test formatting with very long tag names."""
        tags = [
            "service:very-long-service-name-with-many-characters",
            "environment:production-us-west-2-availability-zone-a",
            "team:platform-infrastructure-reliability-engineering",
        ]

        result = format_tags_for_display(tags, max_tags=2)
        # Should still format correctly regardless of tag length
        assert "service:very-long-service-name-with-many-characters" in result
        assert "+1 more" in result

    def test_formatting_consistency(self):
        """Test that formatting is consistent across multiple calls."""
        tags = ["service:web", "env:prod", "team:platform", "version:1.0"]

        result1 = format_tags_for_display(tags, max_tags=2)
        result2 = format_tags_for_display(tags, max_tags=2)
        result3 = format_tags_for_display(tags, max_tags=2)

        # All calls should produce identical output
        assert result1 == result2 == result3

    def test_unicode_in_display(self):
        """Test formatting tags with unicode characters."""
        tags = ["region:🌎", "status:✓", "team:plataforma"]
        result = format_tags_for_display(tags, max_tags=2)

        assert "region:🌎" in result
        assert "status:✓" in result
        assert "+1 more" in result
